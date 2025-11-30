---
slug: introducing-baseboards
title: Introducing Baseboards
authors:
  - cdiddy77
tags:
  - announcement
  - baseboards
  - release
---

<!-- truncate -->

## Generative AI Artifact Creation/Storage/Reuse/Sharing

### Overview

This documentation provides an introduction to the boards toolkit built for generative AI applications, and for the [baseboards](https://www.npmjs.com/package/@weirdfingers/baseboards) CLI, which allows to produce GenAI artifacts on a local system using API keys. It details the setup process, features, and future plans for the project.

**Introduction to Generative AI Boards** [0:10](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=10)

![Example Board](/img/blog/example-board.png)

- The project is inspired by various creative platforms like LTX Studio, OpenArt, and Higgs Field AI, which share a common UI paradigm that we refer to as **boards** for image generation.
- These platforms have common features such as prompt areas for creating images and galleries for generated artifacts.
- The goal is to create a toolkit that allows users to control their own workflows and storage.

**Key Features of the Custom Board** [4:16](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=256)

- **Ultimate Customizability**: Users can tailor the board to their needs.
- **Direct API Access**: Users can use their own API keys for direct access to model providers.
- **User-Controlled Storage**: Images can be stored and backed up according to user preferences.

**Setup Requirements** [4:59](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=299)

- Users must have Node.js and Docker installed on their system (Mac, Windows, or Linux).
- The setup process involves using the command line to initialize the board application.

**Installation Process** [5:39](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=339)

![generated-image-at-00:05:39](/img/blog/quick-setup.png)

1. Open your terminal.
2. Run the command: `npx @weirdfingers/baseboards up my-boards-app` (replace 'my-boards-app' with your desired app name).
3. Enter your API keys when prompted (currently supports Replicate and File).
4. The application will start and run on your local system, typically at `localhost:3300`.

**Using the Board** [6:39](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=399)

![using-the-board](/img/blog/new-board.png)

- After setup, users can create new boards and generate images using various supported models.
- The application supports popular models like Imogen 4, Nano Banana, and Flux, with plans to add more in the future.

**Directory Structure** [8:00](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=480)

![new-project](/img/blog/new-project.png)

- The generated directory contains:
  - `api/`: Backend logic and services.
  - `data/`: Storage for generated files.
  - `docker/`: Docker configuration files.
  - `web/`: Frontend source code.

**Future Plans** [9:36](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46?t=576)

- The project aims to add more models and features based on user requests.
- Improved support for coding, especially for five coding, is planned.
- Community involvement is encouraged through Discord and social media channels.

### Link to Loom

[Watch the full video on Loom](https://loom.com/share/8fca2571cf104e128b1d3acb19d1cd46)
