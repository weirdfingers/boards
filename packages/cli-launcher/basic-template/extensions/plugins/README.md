# Plugins

This directory is for custom plugins that extend the Boards backend functionality.

## Adding Plugins

Plugins allow you to extend the Boards API with custom functionality. To add a plugin:

1. Create a new Python file in this directory with your plugin class
2. Your plugin should implement the plugin interface defined in the Boards package
3. Register your plugin in the backend configuration

## Documentation

For more information on creating plugins, see:
https://boards-docs.weirdfingers.com/docs/generators/configuration

Note: Plugin system is being introduced in PR #231. Check the documentation for the latest plugin API.
