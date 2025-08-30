We are going to create an open source project. We will start by discussing it. Until you receive explicit instructions to do something, I want you to stick to asking clarifying questions. Got it?

Here is the tagline for the project:

A toolkit to create, store, reuse and share generative AI multimedia artifacts

It will need a backend in python, frontend packages in react. It will need examples and it will need documentation, using docusaurus.

Here is the basic getting started scenario:

User wants to create images, audio, videos, and more advanced users want to create LoRAs and even fine tunes of popular open source generative art models. Advanced users may want to run locally, and even use comfyUI workflows, via SaaS providers.

User want to be able to use any of a wide variety of models (flux, veo, qwen-image, various TTS, etc), from any of a variety of different providers (aggregators like replicate and [fal.ai](http://fal.ai), but also directly from black forest labs, google, luma, elevenlabs and others). They don’t want to have to learn all the different apis.

As they create these digital artifacts using these models, they want them all to be available in a single unified storage and interface, partly for easy access, but partly also so they can use some of the outputs as inputs to other models and workflows.

Users want to collaborate with clients and co-workers on these collections of artifacts.

## Use case 1: semi-technical

They use npx or some other simple command to install the CLI. They run the CLI. It runs a script that prompts them for all the various API keys they need in order to use the providers and the models. It is configurable, so users can opt in to whichever models and providers they want. When they are done configuring, then the backend (python) and stock/standard/example frontend (nextjs) are started. They can surf to localhost:3000 and they can log in, and create and edit boards using all of the models and providers they have configured.

## Use case 2: technical

They create a new coding project. They install the CLI via npx, and they add @weirdfingers/boards as a dependency to their e.g. website (requires react). With the CLI, they can configure and run just the backend, and then using the react boards package dependency, they can create their own custom frontend UI, using the various contexts and hooks that encapsulate the data access and generation abilities. They configure the backend with specific providers/generators.

## Use case 3: vibe coder/entrepreneur

They use an AI agent based vibe coding tool to create a product idea that involves generative art. They do development locally, but use accessible deployment services like netlify and vercel. They have some sort of innovative ideas which require deep customization. Because they are hoping to develop into a product, they make use of the authentication features, and the deeper API features around sharing boards. They use every part of the API to stretch the functionality to its limit. They might build their own provider/generator plugins. They create their own custom UI for generating and accessing board content.

## Use case 3.5: no-local vibe coder

Like the vibe coder/entrepreneur, but they prefer to use cloud-based vibe coding tools and may never work locally. They don’t run a backend locally, don’t use local storage, even for development. Therefore they will need the backend and DB/storage to all be cloud-based, even for development.

## Use case 4: advanced

Like the technical use case, but they customize the configuration, potentially adding their own providers (even local ones) or generators, customizing storage, doing cloud based deployments using advanced platform features, implementing their own plugins for auth, storage, database etc They have their own database and have advanced requirements around integrating with boards storage (both DB and storage). Eventually, in order to achieve their goals, they may need to fork the repo and make custom changes to the source code.

## Key Concepts

**Generator** : a component of the system which takes inputs and generates outputs of one of the supported artifact types (image, audio, video, LoRA, …). This can be based on an AI model, e.g. flux, veo, etc.  
**Provider** : a third party, typically a SaaS which provides access to one or more generators (often models).  
**User**: an actor in the system. Has a specific role for a specific set of boards.  
**Generation**: the result or output of a generator executing on a set of inputs, which can include other generations. The generation includes references to the files stored in some sort of online storage, local/remote/… . It also includes metadata about the creation, as well as the inputs, provider job id, etc.  
**Board**: A collection of generations, and attached user role/rights information.
