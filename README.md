[**Support me with a Follow**](https://github.com/shunpochang/followers)

# D3 example on a Bi-directional Drag and Zoom Tree.

[The D3 dependency Demo](http://bl.ocks.org/shunpochang/66620bad0e6b201f261c) is created using **D3.js** and basic crawling on **GitHub** js files to generate tree relationship on D3 development dependencies.

The tree shows the dependencies related to D3 development:
* The upward branches are the repos that D3 is dependent on, from a direct dependency to further parent files that these repos were dependent on.
* The lower branches are repos that are dependent on D3, and the children files that are dependent on these repos.

The main logic to pull these dependencies and generating tree data is in [populate_tree_data/] (https://github.com/shunpochang/d3tree/tree/master/get_tree_from_git), where package.json and bower.json files (to include both NPM and Bower installation) are crawled to get the top matching libraries.

[![alt text](https://github.com/shunpochang/d3tree/blob/master/thumbnail.png "D3 tree")](http://bl.ocks.org/shunpochang/66620bad0e6b201f261c)

