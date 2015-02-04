"""Populate JSON data for D3 tree.

For each direction (upward and downward), we will start from the origin (base
node from D3), and list out more generations of Git libaries dependent on D3
and its future generation, or libraries that D3 is dependent on.

For each node, we will store the name, full path name, and create date.
"""
import collections
import json
import logging
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
    # tree_data for later use.
    for depth in xrange(1, max_depth + 1):
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
    self._json_output['children'] = self.MapChild('d3', 1)
    logging.info(json.dumps(self._json_output))

  def MapChild(self, parent_name, depth):
    """Populate D3-tree-compatible structure for each child.

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
      logging.info('Reaching Max level for %s at depth %d' % (
          parent_name, depth))
      return children_array
    logging.info('Populating Child for %s...' % parent_name)
    parent_dict = self._tree_data[parent_name]
    depth += 1
    num_mapped_children = 0
    for child_name, child_info in parent_dict.iteritems():
      # For downward, we will separate out cases when child_info is {} versus
      # when child_info is False: {} means child_info is already mapped
      # earlier, and thus it should not contain anymore children nodes;
      # whereas False means that they are not part of the dependent files, but
      # rather they are kept in crawling process to prevent repetitive search.
      if child_info == False:
        continue
      child_json = {
          'name': self.GetNodeDisplayName(child_info),
          'direction': self.direction,
          'children': self.MapChild(child_info['name'], depth),
      }
      # Add in repeated flag to differentiate nodes with the same name.
      if child_info == {}:
        child_json['repeated'] = True
      num_mapped_children += 1
      children_array.append(child_json)
    logging.info('%d of children were populated for %s' % (
        num_mapped_children, parent_name))
    return children_array
  
  def GetNodeDisplayName(self, node_object):
    """We will create customized names for tree nodes.
    
    The display is set to be '{path_name} ({create_date})'.

    Args:
      node_name: Dictionary containing the repo detail.

    Returns:
      String for the display name.
    """
    return '{} ({})'.format(
        node_object['full_name'], node_object['created_at'][:4])



if __name__ == '__main__':
  TreeGenerator('downward', 1).PopulateTree()
