const { createHash, randomBytes, randomUUID, scryptSync, timingSafeEqual } = require('crypto')
const { readFileSync } = require('fs')
const express = require('express')
const mongoose = require('mongoose')

const app = express()
const port = Number(process.env.PORT || 3001)
const mongoUrl = process.env.MONGODB_URL || 'mongodb://127.0.0.1:27017/circle_social'

app.disable('x-powered-by')
app.set('trust proxy', true) // correct protocol/IP behind hosting proxies (e.g. Hugging Face, Render)
app.set('json escape', true) // encode <, > and & in JSON so user input is never reflected raw

app.use((_req, res, next) => {
  res.set({
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  })
  next()
})

// CORS (bearer tokens, no cookies) and a simple per-IP rate limit for the API.
const RATE_LIMIT = 300
const RATE_WINDOW_MS = 60 * 1000
const requestCounts = new Map()
setInterval(() => {
  const now = Date.now()
  for (const [key, entry] of requestCounts) if (entry.reset <= now) requestCounts.delete(key)
}, RATE_WINDOW_MS).unref()
app.use('/api', (req, res, next) => {
  res.set({
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  })
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  const now = Date.now()
  let entry = requestCounts.get(req.ip)
  if (!entry || entry.reset <= now) {
    entry = { count: 0, reset: now + RATE_WINDOW_MS }
    requestCounts.set(req.ip, entry)
  }
  entry.count += 1
  res.set({
    'RateLimit-Limit': String(RATE_LIMIT),
    'RateLimit-Remaining': String(Math.max(0, RATE_LIMIT - entry.count)),
    'RateLimit-Reset': String(Math.ceil((entry.reset - now) / 1000)),
  })
  if (entry.count > RATE_LIMIT) return res.status(429).json({ error: 'Too many requests. Try again in a minute.' })
  next()
})

app.use(express.static(`${__dirname}/public`))
app.use(express.json())

const userSchema = new mongoose.Schema({
  name: { type: String, required: true, maxlength: 60 },
  username: { type: String, required: true, unique: true, lowercase: true, match: /^[a-z0-9_]{3,24}$/ },
  passwordHash: { type: String, required: true },
  bio: { type: String, default: '', maxlength: 160 },
}, { timestamps: true })

const commentSchema = new mongoose.Schema({
  author: { type: mongoose.Schema.Types.ObjectId, ref: 'CircleUser', required: true },
  content: { type: String, required: true, maxlength: 280 },
}, { timestamps: true })

const postSchema = new mongoose.Schema({
  author: { type: mongoose.Schema.Types.ObjectId, ref: 'CircleUser', required: true },
  content: { type: String, required: true, maxlength: 280 },
  likes: [{ type: mongoose.Schema.Types.ObjectId, ref: 'CircleUser' }],
  comments: [commentSchema],
}, { timestamps: true })

const sessionSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'CircleUser', required: true },
  tokenHash: { type: String, required: true, unique: true },
  expiresAt: { type: Date, required: true, expires: 0 },
}, { timestamps: true })

const User = mongoose.models.CircleUser || mongoose.model('CircleUser', userSchema, 'users')
const Post = mongoose.models.CirclePost || mongoose.model('CirclePost', postSchema, 'posts')
const Session = mongoose.models.CircleSession || mongoose.model('CircleSession', sessionSchema, 'sessions')

const publicUser = (user) => ({ id: user._id.toString(), name: user.name, username: user.username, bio: user.bio })
function makePasswordHash(password) {
  const salt = randomBytes(16).toString('hex')
  return `${salt}:${scryptSync(password, salt, 64).toString('hex')}`
}
function passwordMatches(password, storedHash) {
  const [salt, hash] = String(storedHash).split(':')
  if (!salt || !hash) return false
  const actual = scryptSync(password, salt, 64)
  const expected = Buffer.from(hash, 'hex')
  return expected.length === actual.length && timingSafeEqual(expected, actual)
}
async function tokenFor(user) {
  const token = randomUUID()
  const tokenHash = createHash('sha256').update(token).digest('hex')
  await Session.create({ user: user._id, tokenHash, expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) })
  return token
}
function tokenHashFrom(req) {
  const token = req.get('Authorization')?.match(/^Bearer (.+)$/)?.[1]
  return token && createHash('sha256').update(token).digest('hex')
}
async function userFromRequest(req) {
  const tokenHash = tokenHashFrom(req)
  const session = tokenHash && await Session.findOne({ tokenHash, expiresAt: { $gt: new Date() } })
  return session && await User.findById(session.user)
}
async function auth(req, res, next) {
  try {
    const user = await userFromRequest(req)
    if (!user) return res.status(401).json({ error: 'Sign in to continue' })
    req.user = user
    next()
  } catch (error) { next(error) }
}
// Like auth, but lets guests through (req.user stays undefined).
async function optionalAuth(req, _res, next) {
  try {
    req.user = (await userFromRequest(req)) || undefined
    next()
  } catch (error) { next(error) }
}
// Reject request bodies with fields an endpoint does not accept (strict input validation).
function rejectUnknownFields(req, res, allowed) {
  const body = req.body
  const extra = body && typeof body === 'object' ? Object.keys(body).filter((key) => !allowed.includes(key)) : []
  if (!extra.length) return false
  res.status(400).json({ error: `Unknown field(s): ${extra.join(', ')}` })
  return true
}
function serialize(post, viewer) {
  return {
    id: post._id.toString(),
    content: post.content,
    createdAt: post.createdAt,
    author: publicUser(post.author),
    likes: post.likes.length,
    liked: Boolean(viewer && post.likes.some((id) => id.equals(viewer._id))),
    comments: post.comments.map((comment) => ({
      id: comment._id.toString(), content: comment.content, createdAt: comment.createdAt, author: publicUser(comment.author),
    })),
  }
}

app.get('/api/health', (_req, res) => res.json({ ok: true, service: 'circle-social', storage: 'mongodb' }))
app.post('/api/auth/register', async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, ['username', 'password', 'name', 'bio'])) return
    const username = String(req.body?.username || '').trim().toLowerCase()
    const name = String(req.body?.name || username).trim()
    const password = String(req.body?.password || '')
    const bio = String(req.body?.bio || '').trim()
    if (!name || name.length > 60 || !/^[a-z0-9_]{3,24}$/.test(username) || password.length < 6 || bio.length > 160) {
      return res.status(400).json({ error: 'Username must be 3–24 lowercase letters, numbers or _, and password at least 6 characters' })
    }
    const user = await User.create({ name, username, passwordHash: makePasswordHash(password), bio })
    res.status(201).json({ user: publicUser(user), token: await tokenFor(user) })
  } catch (error) {
    if (error.code === 11000) return res.status(409).json({ error: 'Username already exists' })
    if (error.name === 'ValidationError') return res.status(400).json({ error: error.message })
    next(error)
  }
})
const MAX_FAILED_LOGINS = 10
const LOGIN_LOCK_MS = 15 * 60 * 1000
const failedLogins = new Map()
app.post('/api/auth/login', async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, ['username', 'password'])) return
    const username = String(req.body?.username || '').trim().toLowerCase()
    const password = String(req.body?.password || '')
    if (!username && !password) return res.status(400).json({ error: 'Enter your username and password' })
    if (!username) return res.status(400).json({ error: 'Username is required' })
    if (!password) return res.status(400).json({ error: 'Password is required' })
    const key = `${req.ip}|${username}`
    const now = Date.now()
    const failures = failedLogins.get(key)
    if (failures && failures.until > now && failures.count >= MAX_FAILED_LOGINS) {
      return res.status(429).json({ error: 'Too many failed sign-in attempts. Try again in 15 minutes.' })
    }
    const user = await User.findOne({ username })
    if (!user || !passwordMatches(password, user.passwordHash)) {
      const entry = failures && failures.until > now ? failures : { count: 0, until: now + LOGIN_LOCK_MS }
      entry.count += 1
      failedLogins.set(key, entry)
      return res.status(401).json({ error: 'Invalid username or password' })
    }
    failedLogins.delete(key)
    res.json({ user: publicUser(user), token: await tokenFor(user) })
  } catch (error) { next(error) }
})
app.get('/api/auth/me', auth, (req, res) => res.json({ user: publicUser(req.user) }))
app.post('/api/auth/logout', auth, async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, [])) return
    await Session.deleteOne({ tokenHash: tokenHashFrom(req) })
    res.json({ ok: true })
  } catch (error) { next(error) }
})
app.get('/api/posts', optionalAuth, async (req, res, next) => {
  try {
    const q = String(req.query.q || '').trim()
    const filter = q ? { content: { $regex: q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), $options: 'i' } } : {}
    const posts = await Post.find(filter).sort({ createdAt: -1 }).populate('author').populate('comments.author')
    res.json({ posts: posts.map((post) => serialize(post, req.user)) })
  } catch (error) { next(error) }
})
app.post('/api/posts', auth, async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, ['content'])) return
    const content = String(req.body?.content || '').trim()
    if (!content || content.length > 280) return res.status(400).json({ error: 'Post content must be 1–280 characters' })
    const post = await Post.create({ author: req.user._id, content })
    await post.populate('author')
    res.status(201).json({ post: serialize(post, req.user) })
  } catch (error) { next(error) }
})
app.post('/api/posts/:id/like', auth, async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, [])) return
    if (!mongoose.isValidObjectId(req.params.id)) return res.status(404).json({ error: 'Post not found' })
    const post = await Post.findById(req.params.id)
    if (!post) return res.status(404).json({ error: 'Post not found' })
    const liked = post.likes.some((id) => id.equals(req.user._id))
    post.likes = liked ? post.likes.filter((id) => !id.equals(req.user._id)) : [...post.likes, req.user._id]
    await post.save()
    res.json({ liked: !liked, likes: post.likes.length })
  } catch (error) { next(error) }
})
app.post('/api/posts/:id/comments', auth, async (req, res, next) => {
  try {
    if (rejectUnknownFields(req, res, ['content'])) return
    const content = String(req.body?.content || '').trim()
    if (!content || content.length > 280) return res.status(400).json({ error: 'Comment content must be 1–280 characters' })
    if (!mongoose.isValidObjectId(req.params.id)) return res.status(404).json({ error: 'Post not found' })
    const post = await Post.findById(req.params.id)
    if (!post) return res.status(404).json({ error: 'Post not found' })
    post.comments.push({ author: req.user._id, content })
    await post.save()
    await post.populate(['author', 'comments.author'])
    res.status(201).json({ post: serialize(post, req.user) })
  } catch (error) { next(error) }
})
app.get('/api/search', async (req, res, next) => {
  try {
    const query = String(req.query.q || '').trim()
    const users = await User.find({ username: { $regex: query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), $options: 'i' } }).limit(10)
    res.json({ users: users.map(publicUser) })
  } catch (error) { next(error) }
})
app.get('/openapi.json', (req, res) => {
  // Read per request (small file) so edits to openapi.json apply without a restart.
  const spec = JSON.parse(readFileSync(`${__dirname}/openapi.json`, 'utf8'))
  // Point API tests at wherever this app is actually served (local or deployed).
  spec.servers = [{ url: `${req.protocol}://${req.get('host')}` }]
  // Fresh example username per download so generated "register" tests don't collide with earlier runs;
  // login uses the same example so a "register, then log in" sequence succeeds.
  const exampleUser = `qa_${randomBytes(3).toString('hex')}`
  spec.components.schemas.Register.properties.username.example = exampleUser
  spec.components.schemas.Login.properties.username.example = exampleUser
  res.json(spec)
})
app.use((_req, res) => res.status(404).json({ error: 'Route not found' }))
app.use((error, _req, res, _next) => {
  if (error.type === 'entity.parse.failed') return res.status(400).json({ error: 'Request body must be valid JSON' })
  if (error.type === 'entity.too.large') return res.status(413).json({ error: 'Request body is too large' })
  console.error(error)
  res.status(500).json({ error: 'Unexpected application error' })
})

async function start() {
  await mongoose.connect(mongoUrl)
  const hasWelcomePost = await Post.exists({ content: 'Welcome to Circle. Create an account to join the conversation.' })
  if (!hasWelcomePost) {
    let welcomeUser = await User.findOne({ username: 'circle' })
    if (!welcomeUser) {
      welcomeUser = await User.create({ name: 'Circle Team', username: 'circle', passwordHash: makePasswordHash(randomUUID()), bio: 'A place for thoughtful conversations.' })
    }
    await Post.create([
      { author: welcomeUser._id, content: 'Welcome to Circle. Create an account to join the conversation.' },
      { author: welcomeUser._id, content: 'Share an idea, respond to a post, and make this community your own.' },
    ])
  }
  app.listen(port, '0.0.0.0', () => console.log(`Circle Social listening on http://127.0.0.1:${port} (MongoDB: ${mongoose.connection.name})`))
}

start().catch((error) => {
  // Never log the password from the connection string.
  const safeUrl = mongoUrl.replace(/\/\/([^:@/]+):[^@]+@/, '//$1:****@')
  console.error(`Could not connect to MongoDB at ${safeUrl}:`, error.message)
  process.exit(1)
})
