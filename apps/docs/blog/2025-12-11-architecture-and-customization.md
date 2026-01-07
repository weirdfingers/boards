---
title: "Architecture and Customization Guide"
date: 2025-12-11
authors: [cdiddy77]
tags: [architecture, customization, backend, frontend, documentation]
description: "A comprehensive overview of the Baseboards project structure, components, and customization options for developers looking to understand and modify their installation."
---

# Baseboards Documentation

Baseboards is an open source npx CLI package which provides a complete platform for generating, storing, reusing and sharing digital artifacts, especially those created with generative AI models.

## Overview

This documentation provides an overview of the Baseboards project, detailing its structure, components, and customization options. It serves as a basic introduction for developers looking to understand and modify the Baseboards installation.

### **Project Structure** [0:00](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=0)

![project structure](/img/blog/251211/project-structure.png)

- The Baseboards project includes files necessary for running the application.
- The project consists of:
  - **Docker Compose** configuration files.
  - **API**: The backend built with FastAPI, utilizing SQLAlchemy for database models.
  - **Data Storage**: By default, data is stored locally, but pluggable storage options for cloud services are available (pending implementation).
  - **Web**: The frontend is built with Next.js, featuring a simple set of dependencies including Tailwind CSS and Bratics controls.

### **Backend Overview** [1:08](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=68)

![backend overview](/img/blog/251211/backend-overview.png)

- The backend is primarily written in Python and is structured as a FastAPI application.
- It includes:
  - Database models using SQLAlchemy.
  - A GraphQL API implemented with Strawberry, allowing for queries and mutations.
  - Workers running in a separate container for independent scaling from the API server.

#### **Generators** [2:29](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=149)

![generators code](/img/blog/251211/generators-code.png)

- Generators are responsible for calling the models and generating content.
- Examples include implementations for audio, video and image processing, such as Nano Banana Pro and Flux 2.
- Users can modify these generators as needed or create their own.

#### **Authentication and Storage** [3:13](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=193)

![storage config](/img/blog/251211/storage.png)

- Current authentication support is limited, but future plans include integration with various auth providers.
- The storage implementation is currently local, with aspirations to support popular cloud storage options like Google Cloud and S3.

### **Frontend Overview** [4:27](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=267)

![frontend overview](/img/blog/251211/frontend-overview.png)

- The frontend is a basic Next.js application.
- Dependencies include the npm package `@weirdfingers/boards` for core functionality.
- Future support for other frameworks like Svelte and Create React App (CRA) is desired.

## **Customization and Features** [9:04](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9?t=544)

![generated-image-at-00:09:04](https://loom.com/i/d5df380cda5345efb401cfeced61d077?workflows_screenshot=true)

- Users have full access to the source code for both the backend and frontend, allowing for extensive customization.
- The video contains a vibe coding session for two such customizations:
  - Simple generic customizations such as adding a dark mode feature.
  - Making use of Boards-specific functionality, such as renaming boards, although this may soon become obviated, as there is an [existing Github issue](https://github.com/weirdfingers/boards/issues/182) for such functionality, marked `good first issue` and `help wanted`

### Link to Loom

[Watch the full video walkthrough](https://loom.com/share/3a88820cd4524f4d81aa1b07ac2905b9)
