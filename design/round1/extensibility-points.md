## Pluggability

The system should work out of the box, but should also support various extensibility points:

- **DB** : must be compatible with SQL Alchemy. Out of the box: Postgresql.
- **Storage** : out of the box must work with local supabase, remote supabase, S3, GCS, and local file system, but also support storage plugins.
- **Authentication** : out of the box it can support no authentication (for prototyping or local use) and authentication via pluggable auth provider (supabase, firebase, auth0, clerk). Note that we don’t have to support logging the user in, or account administration, just auth for purposes of authorizing access to boards.
- **Providers** : This is a critical extensibility point. The universe of models and providers is constantly growing and so we must support simple, flexible, powerful plugin model for providers, as well as providing out of the box support for common providers (replicate, [fal.ai](http://fal.ai), google, openai). Users of the boards toolkit must be able to bring their own providers, and easily set up configuration for providers.
- **Generators** : This is a critical extensibiilty point. The universe of models and providers is constantly growing and so we must support simple, flexible, powerful plugin model for generators (often synonymous with models, but not exclusively). Users of the boards toolkit must be able to bring their own generators.
- **Frontend Authoring** : Each generator can have a very complicated set of inputs. Examples are video generators that take multiple images as input, lip sync video generators that take video and audio as input, and inpainting generators that take image masks and images as input. In order to support these sorts of generators, we need to create a composable set of UI tools for creating arbitrary authoring UIs. This means avoiding components with hard-coded styles, and instead providing custom hooks that expose the state, behavior and backend access necessary.
