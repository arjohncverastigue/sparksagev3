import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "Password",
      credentials: {
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        console.log("Authorize function started.");
        const password = credentials?.password as string;
        if (!password) {
          console.log("Authorize: Password is empty, returning null.");
          return null;
        }

        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          console.log("Authorize: Frontend API URL being used:", apiUrl);
          
          console.log("Authorize: Attempting fetch to:", `${apiUrl}/api/auth/login`);
          const res = await fetch(`${apiUrl}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password }),
          });
          console.log("Authorize: Fetch call completed, response status:", res.status);

          if (!res.ok) {
            console.log("Authorize: Response not OK, status:", res.status, "returning null.");
            // Log response body if not ok
            const errorText = await res.text();
            console.error("Authorize: Error response body:", errorText);
            return null;
          }

          const data = await res.json();
          console.log("Authorize: Received data from backend, checking accessToken.");
          if (!data.access_token) {
              console.log("Authorize: access_token missing in response, returning null.");
              return null;
          }
          console.log("Authorize: Login successful, returning user object.");
          return {
            id: "admin",
            name: "Admin",
            accessToken: data.access_token,
          };
        } catch (error) {
          console.error("Authorize: Caught an error during fetch or processing:", error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as { accessToken: string }).accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      (session as { accessToken?: string }).accessToken = token.accessToken as string;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
});
