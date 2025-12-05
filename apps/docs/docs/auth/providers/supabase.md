# Supabase Authentication

:::caution Under Construction

This documentation has not yet been fully tested with an actual Supabase project. Some steps may be incomplete or require adjustments. We welcome community contributions to validate and improve this guide.

**[Help us test this guide →](https://github.com/weirdfingers/boards/issues/152)**

:::

Use Supabase Auth for managed authentication with social providers, email/password, and more.

## Backend Setup

### Environment Variables

```bash
BOARDS_AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Or configure via JSON:

```bash
BOARDS_AUTH_PROVIDER=supabase
BOARDS_AUTH_CONFIG='{"url": "https://your-project.supabase.co", "service_role_key": "your-key"}'
```

### Supabase Project Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Settings > API to get your URL and keys
3. Configure authentication providers in Auth > Providers
4. Set up redirect URLs in Auth > URL Configuration

## Frontend Setup

### Installation

```bash
npm install @weirdfingers/boards @supabase/supabase-js
```

### Provider Configuration

```typescript
import { SupabaseAuthProvider, AuthProvider } from "@weirdfingers/boards";

const authProvider = new SupabaseAuthProvider({
  url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  tenantId: "my-company", // optional
});

function App() {
  return <AuthProvider provider={authProvider}>{/* Your app */}</AuthProvider>;
}
```

### Configuration Options

| Option     | Default     | Description                     |
| ---------- | ----------- | ------------------------------- |
| `url`      | Required    | Supabase project URL            |
| `anonKey`  | Required    | Supabase anonymous/public key   |
| `tenantId` | `undefined` | Tenant ID for multi-tenant apps |

## Usage

### Email/Password Sign Up

```typescript
import { useAuth } from "@weirdfingers/boards";

function SignUpForm() {
  const { signIn } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    try {
      await signIn({
        type: "signup",
        email: formData.get("email") as string,
        password: formData.get("password") as string,
        options: {
          data: {
            display_name: formData.get("name") as string,
          },
        },
      });
    } catch (error) {
      console.error("Sign up failed:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" placeholder="Full Name" required />
      <input name="email" type="email" placeholder="Email" required />
      <input name="password" type="password" placeholder="Password" required />
      <button type="submit">Sign Up</button>
    </form>
  );
}
```

### Email/Password Sign In

```typescript
function SignInForm() {
  const { signIn } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    try {
      await signIn({
        email: formData.get("email") as string,
        password: formData.get("password") as string,
      });
    } catch (error) {
      console.error("Sign in failed:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" type="email" placeholder="Email" required />
      <input name="password" type="password" placeholder="Password" required />
      <button type="submit">Sign In</button>
    </form>
  );
}
```

### Social Authentication

```typescript
function SocialAuth() {
  const { signIn } = useAuth();

  return (
    <div>
      <button onClick={() => signIn({ provider: "google" })}>
        Continue with Google
      </button>
      <button onClick={() => signIn({ provider: "github" })}>
        Continue with GitHub
      </button>
      <button onClick={() => signIn({ provider: "discord" })}>
        Continue with Discord
      </button>
    </div>
  );
}
```

## Supabase Configuration

### Redirect URLs

Configure these redirect URLs in your Supabase project:

**Development:**

```
http://localhost:3033/auth/callback
```

**Production:**

```
https://yourdomain.com/auth/callback
```

### Email Templates

Customize email templates in Auth > Templates:

- Confirm signup
- Reset password
- Magic link
- Email change confirmation

### Row Level Security (RLS)

Boards handles authorization at the application level, but you can add additional RLS policies:

```sql
-- Example: Users can only access their own data
CREATE POLICY "Users can view own profile" ON users
  FOR SELECT USING (auth.uid()::text = auth_subject);
```

## Advanced Features

### Magic Links

```typescript
function MagicLinkForm() {
  const { signIn } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    await signIn({
      email: formData.get("email") as string,
      options: {
        shouldCreateUser: true,
      },
    });

    alert("Check your email for the magic link!");
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" type="email" placeholder="Email" required />
      <button type="submit">Send Magic Link</button>
    </form>
  );
}
```

### Password Reset

```typescript
function PasswordReset() {
  const [email, setEmail] = useState("");

  const handleReset = async () => {
    // This would call Supabase's resetPasswordForEmail
    // Implementation depends on your auth provider setup
  };

  return (
    <div>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your email"
      />
      <button onClick={handleReset}>Reset Password</button>
    </div>
  );
}
```

## Security Considerations

### RLS Policies

While Boards handles authorization, consider adding Supabase RLS as defense-in-depth:

```sql
-- Enable RLS on your tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE boards ENABLE ROW LEVEL SECURITY;

-- Example policies
CREATE POLICY "Users can access own tenant data" ON boards
  FOR ALL USING (
    tenant_id = (
      SELECT tenant_id FROM users
      WHERE auth_subject = auth.uid()::text
    )
  );
```

### Service Role Key

- Never expose service role key in frontend code
- Use environment variables for server-side configuration
- Rotate keys regularly
- Monitor usage in Supabase dashboard

### CORS Configuration

Supabase automatically handles CORS for your domain, but verify your settings in Auth > URL Configuration.

## Troubleshooting

### Common Issues

**"Invalid login credentials" error:**

- Check email/password are correct
- Verify user has confirmed their email
- Check Auth > Users in Supabase dashboard

**Redirect not working:**

- Verify redirect URLs are configured correctly
- Check for typos in URLs
- Ensure HTTPS in production

**Token not persisting:**

- Check Supabase session configuration
- Verify localStorage isn't being cleared
- Check browser privacy settings

### Debug Mode

Enable Supabase debug logging:

```typescript
const authProvider = new SupabaseAuthProvider({
  url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  options: {
    debug: true,
  },
});
```

### Checking Supabase Logs

Monitor authentication in your Supabase dashboard:

- Go to Auth > Logs to see authentication attempts
- Check Logs > API for request details
- Use Logs > Realtime for live debugging
