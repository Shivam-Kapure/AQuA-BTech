# Circle Social

A standalone Express social-media demo for showcasing posting, comments, likes, search, and account creation. MongoDB stores users, posts, and login sessions.

```bash
npm install
npm run dev
```

The app expects local MongoDB on `mongodb://127.0.0.1:27017` and creates a `circle_social` database with `users`, `posts`, and `sessions` collections. Set `MONGODB_URL` to use another MongoDB connection.

Open [http://127.0.0.1:3001](http://127.0.0.1:3001) after starting the app. Create an account from the sign-in panel, then publish posts, like them, add comments, or search the feed. Accounts and posts remain saved after the server restarts. Your browser session lasts 30 days and is restored after refresh.
