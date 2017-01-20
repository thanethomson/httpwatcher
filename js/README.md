# JavaScript for httpwatcher

The file `httpwatcher.js` is the primary entry point for the
JavaScript code to facilitate live reloading of web pages for
`httpwatcher`.

[webpack](https://webpack.js.org/) is used to package dependencies
to ultimately build the file in the `httpwatcher/scripts` folder
within the Python package.

## Building the JavaScript bundle
Generally you won't need to do this, but in case you really want to,
first make sure you've got NodeJS installed. Then, from the
root directory of the project, run:

```bash
# Make sure you've got webpack and uglify-js installed globally
> npm install -g webpack uglify-js

# Install local development dependencies
> npm install

# Build it
> npm run build
```
