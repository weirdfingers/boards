# Custom Generators

This directory is for custom generator implementations that extend the Boards toolkit.

## Adding Custom Generators

To add a custom generator:

1. Create a new Python file in this directory with your generator class
2. Your generator class should inherit from `boards.generators.base.Generator`
3. Register your generator in `/config/generators.yaml`

Example:

```python
from boards.generators.base import Generator

class MyCustomGenerator(Generator):
    def generate(self, input_data):
        # Your implementation here
        pass
```

Then add to `/config/generators.yaml`:

```yaml
generators:
  - class: "extensions.generators.my_custom_generator.MyCustomGenerator"
    enabled: true
```

## Documentation

For more information on creating custom generators, see:
https://boards-docs.weirdfingers.com/docs/generators/configuration
