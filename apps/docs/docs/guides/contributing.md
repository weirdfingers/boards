---
sidebar_position: 1
---

# Contributing Guide

Learn how to contribute to the Boards open-source project.

## Getting Started

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/boards.git
   cd boards
   ```
3. **Set up the development environment**:
   ```bash
   make install      # Install all dependencies
   make docker-up    # Start PostgreSQL and Redis
   make upgrade-db   # Run database migrations
   make dev          # Start development servers
   ```

   > 📖 For a complete list of commands, see the [Makefile Commands Reference](./makefile-commands).

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Format and test your changes**:
   ```bash
   make format        # Auto-fix formatting and linting issues
   make test          # Run all tests
   make lint          # Check for remaining issues
   make typecheck     # Verify types
   ```

   > 📖 See the [Makefile Commands Reference](./makefile-commands) for a complete list of available commands.

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Standards

### Python Code Style

- **PEP 8** compliance via `ruff`
- **Type hints** required for all functions
- **Docstrings** for public APIs
- **pytest** for testing

```python
def process_generation(
    generation_id: str,
    params: Dict[str, Any],
) -> GenerationResult:
    """Process a generation request.
    
    Args:
        generation_id: Unique identifier for the generation
        params: Generation parameters
        
    Returns:
        The processing result
        
    Raises:
        ValueError: If generation_id is invalid
    """
    # Implementation here
    pass
```

### TypeScript/React Code Style

- **ESLint** and **Prettier** for formatting
- **TypeScript strict mode**
- **React hooks** patterns
- **JSDoc** for complex functions

```tsx
interface BoardCardProps {
  board: Board;
  onSelect: (board: Board) => void;
}

/**
 * Displays a board card with title, description, and actions.
 */
export function BoardCard({ board, onSelect }: BoardCardProps) {
  return (
    <div onClick={() => onSelect(board)}>
      <h3>{board.title}</h3>
      <p>{board.description}</p>
    </div>
  );
}
```

### Commit Message Format

Use [Conventional Commits](https://conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Build process or auxiliary tool changes

Examples:
```
feat(providers): add Stability AI integration
fix(auth): resolve token refresh issue
docs: update installation guide
```

## Testing Guidelines

### Backend Tests

```python
# tests/test_providers.py
import pytest
from boards.providers.replicate import ReplicateProvider

@pytest.mark.asyncio
async def test_replicate_image_generation():
    provider = ReplicateProvider()
    result = await provider.generate_image(
        prompt="test prompt",
        params={"width": 512, "height": 512}
    )
    assert result.status == "completed"
    assert result.output.url is not None
```

### Frontend Tests

```tsx
// __tests__/hooks/useBoards.test.tsx
import { renderHook } from '@testing-library/react';
import { useBoards } from '@weirdfingers/boards';
import { BoardsProvider } from '../test-utils';

test('should fetch boards on mount', async () => {
  const { result } = renderHook(() => useBoards(), {
    wrapper: BoardsProvider,
  });

  expect(result.current.isLoading).toBe(true);
  
  // Wait for loading to complete
  await waitFor(() => {
    expect(result.current.isLoading).toBe(false);
  });
  
  expect(result.current.boards).toHaveLength(0);
});
```

## Documentation

### API Documentation

Use docstrings and type hints for automatic API documentation generation:

```python
class BoardService:
    """Service for managing boards and their content."""
    
    async def create_board(
        self,
        title: str,
        description: Optional[str] = None,
        tenant_id: str,
    ) -> Board:
        """Create a new board.
        
        Args:
            title: The board title
            description: Optional board description
            tenant_id: The tenant identifier
            
        Returns:
            The created board instance
        """
```

### User Documentation

- Write clear, concise documentation
- Include code examples
- Add screenshots for UI features
- Test all examples before submitting

## Contributing Areas

### High-Priority Contributions

1. **Provider Integrations**
   - New AI service providers
   - Improved error handling
   - Performance optimizations

2. **Frontend Components**
   - UI component examples
   - Accessibility improvements
   - Mobile responsiveness

3. **Documentation**
   - Tutorial improvements
   - API documentation
   - Example projects

4. **Testing**
   - Increase test coverage
   - Integration tests
   - Performance tests

### Feature Requests

Before implementing major features:

1. **Open an issue** to discuss the feature
2. **Get feedback** from maintainers
3. **Create a design document** for complex features
4. **Implement incrementally** with regular feedback

## Code Review Process

### Pull Request Guidelines

- **Clear description** of changes
- **Link to related issues**
- **Include tests** for new functionality
- **Update documentation** as needed
- **Keep PRs focused** and reasonably sized

### Review Criteria

Reviewers will check:
- Code quality and style
- Test coverage
- Documentation updates
- Breaking change considerations
- Performance impact
- Security implications

## Community

### Communication

- **GitHub Discussions** - General questions and ideas
- **GitHub Issues** - Bug reports and feature requests
- **Pull Requests** - Code contributions

### Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct. Be respectful, inclusive, and constructive in all interactions.

## Recognition

Contributors are recognized in:
- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **Documentation** for major features

Thank you for contributing to Boards! 🎨
