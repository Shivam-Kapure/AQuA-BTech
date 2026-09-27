const { createHash, randomBytes, randomUUID, scryptSync, timingSafeEqual } = require('crypto')
const express = require('express')
const mongoose = require('mongoose')

const app = express()
const port = Number(process.env.PORT || 3001)
const mongoUrl = process.env.MONGODB_URL || 'mongodb://127.0.0.1:27017/circle_social'
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
async function auth(req, res, next) {
  try {
    const token = req.get('Authorization')?.match(/^Bearer (.+)$/)?.[1]
    const tokenHash = token && createHash('sha256').update(token).digest('hex')
    const session = tokenHash && await Session.findOne({ tokenHash, expiresAt: { $gt: new Date() } })
    const user = session && await User.findById(session.user)
    if (!user) return res.status(401).json({ error: 'Sign in to continue' })
    req.user = user
    next()
  } catch (error) { next(error) }
}
function serialize(post) {
  return {
    id: post._id.toString(),
    content: post.content,
    createdAt: post.createdAt,
    author: publicUser(post.author),
    likes: post.likes.length,
    comments: post.comments.map((comment) => ({
      id: comment._id.toString(), content: comment.content, createdAt: comment.createdAt, author: publicUser(comment.author),
    })),
  }
}

app.get('/api/health', (_req, res) => res.json({ ok: true, service: 'circle-social', storage: 'mongodb' }))
app.post('/api/auth/register', async (req, res, next) => {
  try {
    const name = String(req.body?.name || '').trim()
    const username = String(req.body?.username || '').trim().toLowerCase()
    const password = String(req.body?.password || '')
    const bio = String(req.body?.bio || '').trim()
    if (!name || name.length > 60 || !/^[a-z0-9_]{3,24}$/.test(username) || password.length < 6 || bio.length > 160) {
      return res.status(400).json({ error: 'Provide a name, a 3–24 character username, and a password of at least 6 characters' })
    }
    const user = await User.create({ name, username, passwordHash: makePasswordHash(password), bio })
    res.status(201).json({ user: publicUser(user), token: await tokenFor(user) })
  } catch (error) {
    if (error.code === 11000) return res.status(409).json({ error: 'Username already exists' })
    if (error.name === 'ValidationError') return res.status(400).json({ error: error.message })
    next(error)
  }
})
app.post('/api/auth/login', async (req, res, next) => {
  try {
    const username = String(req.body?.username || '').trim().toLowerCase()
    const user = await User.findOne({ username })
    if (!user || !passwordMatches(String(req.body?.password || ''), user.passwordHash)) {
      return res.status(401).json({ error: 'Invalid username or password' })
    }
    res.json({ user: publicUser(user), token: await tokenFor(user) })
  } catch (error) { next(error) }
})
app.get('/api/auth/me', auth, (req, res) => res.json({ user: publicUser(req.user) }))
app.get('/api/posts', async (req, res, next) => {
  try {
    const q = String(req.query.q || '').trim()
    const filter = q ? { content: { $regex: q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), $options: 'i' } } : {}
    const posts = await Post.find(filter).sort({ createdAt: -1 }).populate('author').populate('comments.author')
    res.json({ query: q, posts: posts.map(serialize) })
  } catch (error) { next(error) }
})
app.post('/api/posts', auth, async (req, res, next) => {
  try {
    const content = String(req.body?.content || '').trim()
    if (!content || content.length > 280) return res.status(400).json({ error: 'Post content must be 1–280 characters' })
    const post = await Post.create({ author: req.user._id, content })
    await post.populate('author')
    res.status(201).json({ post: serialize(post) })
  } catch (error) { next(error) }
})
app.post('/api/posts/:id/like', auth, async (req, res, next) => {
  try {
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
    const content = String(req.body?.content || '').trim()
    if (!content || content.length > 280) return res.status(400).json({ error: 'Comment content must be 1–280 characters' })
    const post = await Post.findById(req.params.id)
    if (!post) return res.status(404).json({ error: 'Post not found' })
    post.comments.push({ author: req.user._id, content })
    await post.save()
    await post.populate('author').populate('comments.author')
    res.status(201).json({ post: serialize(post) })
  } catch (error) { next(error) }
})
app.get('/api/search', async (req, res, next) => {
  try {
    const query = String(req.query.q || '').trim()
    const users = await User.find({ username: { $regex: query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), $options: 'i' } }).limit(10)
    res.json({ query, users: users.map(publicUser) })
  } catch (error) { next(error) }
})
app.get('/openapi.json', (_req, res) => res.sendFile(`${__dirname}/openapi.json`))
app.use((_req, res) => res.status(404).json({ error: 'Route not found' }))
app.use((error, _req, res, _next) => {
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
  console.error(`Could not connect to MongoDB at ${mongoUrl}:`, error.message)
  process.exit(1)
})
