## Adding a Generator

Generators define inputs, outputs, and how to call a provider. Prefer a declarative YAML spec over Python code.

### 1) Create a spec in `generators.yaml`

```yaml
generators:
  - name: my-image-gen
    display_name: My Image Gen
    artifact_type: image
    provider: replicate
    docs: https://replicate.com/some/model/api
    io:
      input_schema:
        type: object
        properties:
          prompt: { type: string }
          width: { type: integer, default: 1024 }
          height: { type: integer, default: 1024 }
        required: [prompt]
      output_schema:
        type: object
        properties:
          images: { type: array, items: { type: string, format: uri } }
    execution:
      type: rest
      submit:
        method: POST
        path: /predictions
        json:
          version: "<model-version>"
          input:
            prompt: "${input.prompt}"
            width: "${input.width}"
            height: "${input.height}"
      poll:
        method: GET
        path: /predictions/${job.id}
      extract:
        output_paths: ["output"]
```

### 2) Test generation

- Ensure the referenced provider is configured and credentials are set
- Trigger generation via GraphQL/REST or a simple script

### 3) Optional: Custom Python

Only if the REST executor cannot cover the use case (e.g., websockets). Create a subclass of `BaseGenerator` and register it in the registry.

### Tips

- Use JSON Schema constraints (`enum`, `minimum`, `pattern`) for better UI.
- Use `${input.*}` token substitution to map inputs into request payloads.

