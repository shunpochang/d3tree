"""Utility file for all D3 tree."""

import collections
import cPickle
import json
import os
# Using pprint instead of the usual logging as I am doing data exploration as
# well at the same time, and will need to see the data structure.
from pprint import pprint
import sys
import urllib2 as url

# Add authentication and accept format to Git API request, for the basic
# crawler, we set token as the first argument.
API_HEADERS = [
    ('Accept', 'application/vnd.github.v3.text-match+json'),
    ('Authorization', 'token {user_token}'.format(
        user_token=(sys.argv[1] or None))),
]


def PickleTree(tree_data, file_name):
  """Pickle output tree into file.

  Will dump the tree output to file in ./data/{file_name}.pcl.

  Args:
    tree_data: Dictionary of tree info to be pickled.
    file_name: String for pickle file name to dump data in.
  """
  pcl_file = os.path.join(os.path.dirname(__file__), 'data', '{}.pcl'.format(
      file_name))
  with open(pcl_file, 'wb') as pcl:
    cPickle.dump(tree_data, pcl, protocol=-1)
  pprint('Pickled: %s (%d parent results)' % (
      file_name, len(tree_data)))


def GetTreePickle(file_name):
  """Get the dictionary for tree info.

  Due to hourly limit on GitHub search, will constantly store info into pickle
  dump, and retrieve the pickle file whenever applicable.

  Args:
    file_name: String for pickle file name to retrieve data from.

  Returns:
    Either empty or the found pickled tree dictionary.
  """
  pcl_file = os.path.join(os.path.dirname(__file__), 'data', '{}.pcl'.format(
      file_name))
  if os.path.isfile(pcl_file):
    with open(pcl_file, 'rb') as pcl:
      tree_dict = cPickle.load(pcl)
      pprint('Get pickled %s.' % file_name)
      return tree_dict
  return collections.defaultdict(dict)


def GitURLOpener(git_url):
  """Read content from GitHub API.

  Will add in headers to help make authorized calls with better formatting.

  Args:
    git_url: String for GitHub API URL.

  Returns:
    Tuple with (dictionary for response JSON content, integer for remaining
    query rate).
  """
  req = url.Request(url=git_url)
  for header in API_HEADERS:
    req.add_header(*header)
  try:
    response = url.urlopen(req)
  # If no such content exists, throw and error and return empty output.
  except url.HTTPError, err:
    pprint('Cannot retrieve URL info, http error %s' % err)
    return ({}, 0)
  content = json.loads(response.read())
  remain_limit = int(response.info().getheader('X-RateLimit-Remaining'))
  pprint('Retrieved response for %s, now with %s remaining limit' % (
      git_url, remain_limit))
  return (content, remain_limit)


def CreateAllDependentRepos(direction, end_depth):
  """Create the total dependent unique repo names.

  Create a set that contains all found repo names that are dependent on the
  overall tree nodes.

  Args:
    direction: String for tree crawling direction.
    end_depth: Integer for the ending raw_data file to go through to create the
        all_searched_repo file.
  """
  all_dependend_repos = set()
  for depth in xrange(1, (end_depth + 1)):
    data_file = GetTreePickle('{}_raw_data_depth_{}'.format(
        direction, depth))
    pprint('Looping through %d parent nodes in depth %d' % (
        len(data_file), depth))
    for parent, children in data_file.iteritems():
      matched_repo_names = [
          child_name for child_name, child_info in children.iteritems()
          if child_info]
      pprint('%s has %d dependent repos out of %d total searched repos.' % (
          parent, len(matched_repo_names), len(children)))
      all_dependend_repos |= set(matched_repo_names)
  PickleTree(all_dependend_repos, '{}_all_dependent_repo_names'.format(
      direction))
