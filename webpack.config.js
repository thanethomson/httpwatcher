/**
 * webpack configuration for httpwatcher
 */

var path = require('path');

module.exports = {
    entry: "./js/httpwatcher.js",
    output: {
        path: path.resolve(__dirname, path.join('httpwatcher', 'scripts')),
        filename: 'httpwatcher.bundle.js'
    }
};
