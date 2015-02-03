"""Basic GitHub crawler to look for D3 generation info.

For downward search, start with D3 as a keyword, and find repositories that
best match the keyword-search, and then restrict to files with d3 in respecitve
bower.json/package.json file as a proxy for dependencies. Then repeaet the
process for the children nodes to get ther respective dependent repos.

For upward search, repeat the search for all dependencies of D3 by looking at
dependencies listed in bower.json/package.json as the, and find the subsequent
dependcies of the parent nodes.
"""

import base64
import collections
import json
# Using pprint instead of the usual logging as I am doing data exploration as
# well at the same time, and will need to see the data structure.
from pprint import pprint
import re
import time

import utilities as util

GIT_SEARCH_API = 'https://api.github.com/{q}'

# Since most of the files we check against are front-end scripts, we first
# check if bower.json has the dependency, and then check in package.json.
VERIFY_FILES = ('bower', 'package')


class GitCrawler(object):
  """Crawler to go through GitHub and find library name.

  First search through repo queries and then use script search to verify
  if there is a matched dependency in bower.json or package.json.

  Attributes:
    keyword: String for GitHub repo name, which will be used as a search
        keyword.
    direction: String for children direction that the crawler is getting.
    tree_depth: Integer for depths of tree data, starts from 0 as base level.
  """

  def __init__(self, keyword, direction, tree_depth):
    """Set up basic search connectors.

    Args:
      keyword: String for GitHub repo name, which will be used as a search
          keyword.
      direction: String for children direction that the crawler is getting.
      tree_depth: Integer for depths of tree data, starts from 0 as base level.
    """
    pprint('==Initiazliazing crawler for %s for %s...==' % (keyword, direction))
    self.keyword = keyword
    self.direction = direction
    self.tree_depth = tree_depth
    # DefaultDict that stores the search's future generation info.
    self._raw_data_file_name = '{}_raw_data_depth_{}'.format(
        direction, tree_depth)
    self._all_repos_file_name = '{}_all_dependent_repo_names'.format(
        direction)
    self._tree_dict = util.GetTreePickle(
        self._raw_data_file_name) or collections.defaultdict(dict)
    # Read in cumulative repo names to get overall names that have been
    # found with matching dependencies. If not found, use set as default.
    self._all_dependent_repo_names = util.GetTreePickle(
        self._all_repos_file_name) or set()
    # We currently only search for JavaScript repositories.
    self._repo_url = GIT_SEARCH_API.format(
        q='search/repositories?per_page=100&{q_params}'.format(
            q_params='q={}+language:js&sort=stars&order=desc'.format(keyword)))
    self._script_url = GIT_SEARCH_API.format(
        q='repos/{path}/contents/{file}.json')

  # The following two functions are for downward population.
  def GetdownwardRepoList(self):
    """For downward, get a list of all repositories with matching queries.

    We will get matching repositories and take the top 100 items and store the
    item's name and create time as key-value pair.
    """
    query_output, _ = util.GitURLOpener(self._repo_url)
    pprint('Checking dependency through %d found repos ...' % (
        min(query_output['total_count'], 100)))
    tree = self._tree_dict[self.keyword]
    # We will limit each level to be 60 - 10 * depth to restrict data layout,
    # for example, the first depth will have at most 50 children nodes, and
    # each node at depth 5 will at most contain 10 children nodes.
    children_count = 0
    for item in query_output['items']:
      if children_count >= (60 - (10 * self.tree_depth)):
        break
      item_name = item['name']
      # Skip any repositories that have the same name as keyword, as that may be
      # a self reference; also skip if there happens to be a repeated search
      # term in the same depth (including a previous no match);
      if item_name == self.keyword or item_name in tree:
        continue
      dependencies = self.RepoHasDependency(item['full_name'])
      if dependencies:
        item['all_dependencies'] = dependencies
        # If the matched dependency file is already created earlier in other
        # depth, do not keep further nodes to prevent future search.
        tree[item_name] = item
        if item_name in self._all_dependent_repo_names:
          tree[item_name] = {}
        self._all_dependent_repo_names.add(item_name)
        children_count += 1
      # Still store the repo if there is no dependency so that we don't go back
      # and rerun this repo.
      else:
        tree[item_name] = False
      util.PickleTree(self._tree_dict, self._raw_data_file_name)
      util.PickleTree(self._all_dependent_repo_names, self._all_repos_file_name)
    pprint('%d repos were found that are dependent on %s' % (
        children_count, self.keyword))

  def RepoHasDependency(self, repo_full_name):
    """Checks if the repository specifies dependency of the keyword file.

    Args:
      repo_full_name: String for the children repository full name to verify
          dependency for.

    Returns:
      Dictionary for all the dependicies of this repo, and False if the
          specified keyword is not found in the dependency.
    """
    for file_name in VERIFY_FILES:
      file_output, _ = util.GitURLOpener(self._script_url.format(
          path=repo_full_name, file=file_name))
      if 'content' in file_output:
        file_dependencies = self.CheckDependency(file_output)
        if file_dependencies:
          pprint('Found dependency in %s (%d dependencies) in %s' % (
              file_name, len(file_dependencies), repo_full_name))
          return file_dependencies
    pprint('%s has no dependency of %s.' % (repo_full_name, self.keyword))
    return False

  # The following two functions are for upward population.
  def GetupwardRepoList(self):
    """For upward, get the repository detail for the keyword.

    We will search for the top 100 items and return the respository for
    item matching keyword.
    """
    # Skip population if the repo is already found with dependencies.
    if self.keyword in self._all_dependent_repo_names:
      pprint('Repo detail for %s was already included.' % self.keyword)
    query_output, _ = util.GitURLOpener(self._repo_url)
    pprint('Getting keyword repo detail through %d found repos ...' % (
        min(query_output['total_count'], 100)))
    # pylint: disable=undefined-loop-variable
    for item in query_output['items']:
      item_name = item['name']
      if item_name == self.keyword:
        pprint('Repo detail found for %s.' % item_name)
        break
    # Break function if no repo detail is found.
    if not query_output['total_count'] or item_name != self.keyword:
      pprint('%s is not found with repo detail.' % self.keyword)
      return

    all_unique_dependencies = self.GetDependency(item['full_name'])
    # If the matched dependency file is already created earlier in other
    # depth, do not keep further nodes to prevent future search.
    for repo_name in all_unique_dependencies:
      if repo_name in self._all_dependent_repo_names:
        all_unique_dependencies[repo_name] = ''
    item['all_dependencies'] = all_unique_dependencies
    self._tree_dict[self.keyword] = item
    self._all_dependent_repo_names.add(item_name)

    util.PickleTree(self._tree_dict, self._raw_data_file_name)
    util.PickleTree(self._all_dependent_repo_names, self._all_repos_file_name)
    pprint('%d dependencies are found for %s.' % (
        len(all_unique_dependencies), self.keyword))

  def GetDependency(self, repo_full_name):
    """Get all the dependent repo names for the keyword file.

    Args:
      repo_full_name: String for repository full name to get dependency for.

    Returns:
      Dict for all the unique dependicies of this repo, and [] if nothing found.
    """
    all_dependencies = {}
    for file_name in VERIFY_FILES:
      file_output, _ = util.GitURLOpener(self._script_url.format(
          path=repo_full_name, file=file_name))
      if 'content' in file_output:
        file_dependencies = self.CheckDependency(file_output)
        if file_dependencies:
          all_dependencies.update(file_dependencies)
          pprint('Found dependency in %s (%d total dependencies) in %s' % (
              file_name, len(file_dependencies), repo_full_name))
    return all_dependencies

  def CheckDependency(self, file_output):
    """Check if dependency is in the specified file (either Bower or Package).

    Will first decode the content with base64, and then sanitize dependencies
    and keyword strings to allow accurate comparison.

    Args:
      file_output: String for content object in Base64 encoding.

    Returns:
      For downward, if the keyword is found in the dependency section, then
          return dependency dicitonary, else return False.
      For upward, return the dependencies.
    """
    # If contents are not properly formatted, we will skip to the end.
    try:
      file_content = json.loads(base64.b64decode(file_output['content']))
    except ValueError:
      pprint('Could not load dependency content!')
      return False
    if 'dependencies' in file_content:
      dependencies = file_content['dependencies']
      if self.direction == 'upward':
        return dependencies
      rep = re.compile(r'(\.|\-|\s)')
      sanitized_keyword = rep.sub('', self.keyword.lower())
      sanitized_dep_keys = [
          rep.sub('', key.lower()) for key in dependencies.keys()]
      if sanitized_keyword in sanitized_dep_keys:
        return dependencies
    return False


def LoopThroughDepths(direction, start_depth, end_depth=5):
  """Loop through various depth to get corresponding output.

  Args:
    direction: String for directions to crawl through.
    start_depth: Integer for the starting depth to loop through.
    end_depth: Integer for the ending depth to loop through, default to 5.
  """
  # Set the repo generation name based on direction.
  method_name = 'Get{}RepoList'.format(direction)
  if start_depth == 1:
    getattr(GitCrawler('d3', direction, 1), method_name)()
    # Increment start_depth by 1 to allow following populations.
    start_depth += 1
    if end_depth <= 1:
      return
  for depth in xrange(start_depth, (end_depth + 1)):
    parent_file = '{}_raw_data_depth_{}'.format(direction, (depth - 1))
    for parent, children in util.GetTreePickle(parent_file).iteritems():
      # We will generate the keyword dict to loop through based on direction
      # For downward, the group contains keys in children where the
      # corresponding values are not null (which was set so for non-dependent
      # repos or repos that are already searched).
      # For upward, the group will be keys in the dependency dictionary we
      # searched for.
      keyword_dict = children[
          'all_dependencies'] if direction == 'upward' else children
      for child_name, child_info in keyword_dict.iteritems():
        # Exclude all none-dependent files or already searched files.
        if not child_info:
          continue
        pprint('==Generating Git data for %s in %s...==' % (
            child_name, parent))
        getattr(GitCrawler(child_name, direction, depth), method_name)()
        pprint('Sleeping for 5 seconds to allow regeneration of rate limit.')
        time.sleep(5)


if __name__ == '__main__':
  # If we need to start rerun from a cercertain step run CreateAllDependentRepos
  # ; usage example: util.CreateAllDependentRepos('downward', 2)
  # Get all git data for 6 depths.
  LoopThroughDepths('downward', 1)
  LoopThroughDepths('upward', 1, 6)

