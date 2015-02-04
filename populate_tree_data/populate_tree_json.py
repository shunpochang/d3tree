"""Populate JSON data for D3 tree.

For each direction (upward and downward), we will start from the origin (base
node from D3), and list out more generations of Git libaries dependent on D3
and its future generation, or libraries that D3 is dependent on.

For each node, we will store the name, full path name, and create date.
"""
import collections
import json
import logging
import os
import utilities as util

logging.basicConfig(level=logging.DEBUG)


class TreeGenerator(object):
  """Generate tree JSON for either upward or downward.

  The output will be a JSON object that contains children libraries for levels
  specifed by the depth number.

  Attributes:
    direction: String for direction to generate tree for.
    max_depth: Integer for number of depths to populate tree for.
  """

  def __init__(self, direction, max_depth):
    """Initialize tree data and tree output.

    Args:
      direction: String for direction to generate tree for.
      max_depth: Integer for number of depths to populate tree for.
    """
    self.direction = direction
    self.max_depth = max_depth
    self._tree_data = collections.defaultdict(dict)
    # Get existing data from the populated raw data file, and update overall
    # tree_data for later use. Adding depth buffer for upward population as the
    # data layout requires an additional level for the children info.
    depth_buffer = 1 if direction == 'upward' else 0
    for depth in xrange(1, max_depth + 1 + depth_buffer):
      self._tree_data.update(util.GetTreePickle('{}_raw_data_depth_{}'.format(
          direction, depth)))
    # Start from the base level, and we will name it origin to separate it from
    # the rest of the nodes.
    self._json_output = {
        'name': 'origin',
        'direction': direction,
    }

  def PopulateTree(self):
    """Populate tree for the direction.

    We will start with the original node, where parent name is D3, and
    propagate through the rest of the tree.
    """
    self._json_output['children'] = getattr(self, 'Map{}Child'.format(
        self.direction))('d3', 1)
    json_file = os.path.join(os.path.dirname(
        __file__), 'data', '{}_tree_data.json'.format(self.direction))
    with open(json_file, 'w') as js:
      json.dump(self._json_output, js)
    logging.info('Output tree to json file for %s', self.direction)

  # pylint: disable=g-explicit-bool-comparison
  def MapdownwardChild(self, parent_name, depth):
    """Populate D3-tree-compatible structure for each downward child.

    For each child node, from the tree dictionary, get the children keys and
    children generation, and recurse through the same function to get future
    generation details.

    Args:
      parent_name: String for parent node name.
      depth: Integer for the depth level the children are in, and we use it to
          terminate the overall population if it exceeds the max cap.

    Returns:
      List of children array.
    """
    children_array = []
    # If depth exceeds the max amount, return empty array.
    if depth > self.max_depth:
      return children_array
    logging.info('Populating child for %s...', parent_name)
    depth += 1
    num_mapped_children = 0
    for child_name, child_info in self._tree_data[parent_name].iteritems():
      # For downward, we will separate out cases when child_info is {} versus
      # when child_info is False: {} means child_info is already mapped
      # earlier, and thus it should not contain anymore children nodes;
      # whereas False means that they are not part of the dependent files, but
      # rather they are kept in crawling process to prevent repetitive search.
      if child_info == False:
        continue
      child_json = {
          'name': self.GetNodeDisplayName(child_info),
          'children': self.MapdownwardChild(child_name, depth),
      }
      # Add in repeated flag to differentiate nodes with the same name.
      if child_info == {}:
        child_json['repeated'] = True
      num_mapped_children += 1
      children_array.append(child_json)
    logging.info('%d of children were populated for %s',
                 num_mapped_children, parent_name)
    return children_array

  def MapupwardChild(self, parent_name, depth):
    """Populate D3-tree-compatible structure for each upward child.

    For each child node, from their children array, get the children keys and
    find the children info from the tree dictionary, and recurse through the
    same function to get future generation details.
    Using parent_object would avoid re-calling the same object twice, but to
    allow reuseable PopulateTree code, plus there are only little nodes to loop
    through, we will stick with parent_name.

    Args:
      parent_name: String for parent node name.
      depth: Integer for the depth level the children are in, and we use it to
          terminate the overall population if it exceeds the max cap.

    Returns:
      List of children array.
    """
    children_array = []
    # If depth exceeds the max amount, return empty array.
    if depth > self.max_depth:
      return children_array
    logging.info('Populating child for %s...', parent_name)
    depth += 1
    num_mapped_children = 0
    for child_name, child_info in self._tree_data[parent_name][
        'all_dependencies'].iteritems():
      # For upward, we will separate out cases when child_info is '' versus
      # when child info is not found: '' means child_info is already mapped
      # earlier, and thus it should not contain anymore children nodes;
      # whereas if child info is not found int the tree dictionary, it  means
      # that they are not part of the dependent files.
      if child_name not in self._tree_data:
        continue
      child_detail = self._tree_data[child_name]
      child_json = {
          'name': self.GetNodeDisplayName(child_detail),
          'children': self.MapupwardChild(child_name, depth),
      }
      # Add in repeated flag to differentiate nodes with the same name.
      if child_info == '':
        child_json['repeated'] = True
      num_mapped_children += 1
      children_array.append(child_json)
    logging.info('%d of children were populated for %s',
                 num_mapped_children, parent_name)
    return children_array

  def GetNodeDisplayName(self, node_object):
    """We will create customized names for tree nodes.

    The display is set to be '{path_name} ({create_date})'.

    Args:
      node_object: Dictionary containing the repo detail.

    Returns:
      String for the display name.
    """
    return '{} ({})'.format(
        node_object['full_name'], node_object['created_at'][:4])


if __name__ == '__main__':
  TreeGenerator('downward', 5).PopulateTree()
  TreeGenerator('upward', 5).PopulateTree()
