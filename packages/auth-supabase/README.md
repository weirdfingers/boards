# @weirdfingers/auth-supabase

Supabase authentication provider for Boards.

## Installation

```bash
npm install @weirdfingers/auth-supabase @supabase/supabase-js
```

## Usage

```typescript
import { SupabaseAuthProvider } from "@weirdfingers/auth-supabase";
import { AuthProvider } from "@weirdfingers/boards";

const authProvider = new SupabaseAuthProvider({
  url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  tenantId: "my-company", // optional
});

function App() {
  return <AuthProvider provider={authProvider}>{/* Your app */}</AuthProvider>;
}
```

## Configuration

See the [Supabase authentication guide](https://docs.weirdfingers.dev/auth/providers/supabase) for detailed setup instructions.

## Features

- Email/password authentication
- Social provider login (Google, GitHub, Discord, etc.)
- Magic link authentication
- Password reset
- Session management
- TypeScript support

## License

MIT
