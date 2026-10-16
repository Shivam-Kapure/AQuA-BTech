const state = { token: localStorage.getItem('circle-session'), user: null, query: '' }
const $ = (selector) => document.querySelector(selector)
const feed = $('#feed')
const template = $('#post')

async function api(path, options = {}) {
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
  }
  const response = await fetch(path, { ...options, headers })
  const data = await response.json()
  if (!response.ok) {
    if (response.status === 401 && state.token) clearSession()
    throw Error(data.error || 'Request failed')
  }
  return data
}

// Inline messages replace browser alerts: kind is 'error' or 'success'.
function showMessage(element, text, kind = 'error') {
  element.textContent = text
  element.classList.remove('hidden', 'error', 'success')
  element.classList.add(kind)
  // Per-post message slots only become live regions while they show something,
  // so [role=alert] never matches the empty slots in every post card.
  if (element.classList.contains('post-message')) element.setAttribute('role', 'alert')
}
function hideMessage(element) {
  element.textContent = ''
  element.classList.add('hidden')
  if (element.classList.contains('post-message')) element.removeAttribute('role')
}

function clearSession() {
  state.user = null
  state.token = null
  localStorage.removeItem('circle-session')
  $('#session').textContent = 'Guest mode'
  $('#logout').classList.add('hidden')
  $('#auth-panel').classList.remove('hidden')
  $('#account').classList.add('hidden')
  $('#composer').classList.add('hidden')
  $('#composer-guest').classList.remove('hidden')
}

function setUser(user) {
  state.user = user
  $('#session').textContent = `@${user.username}`
  $('#logout').classList.remove('hidden')
  $('#auth-panel').classList.add('hidden')
  $('#account').classList.remove('hidden')
  $('#account-name').textContent = user.name
  $('#account-username').textContent = `@${user.username}`
  $('#composer').classList.remove('hidden')
  $('#composer-guest').classList.add('hidden')
}

function signedIn(data) {
  state.token = data.token
  localStorage.setItem('circle-session', data.token)
  $('#auth').reset()
  hideMessage($('#auth-message'))
  setUser(data.user)
  load()
}

async function signOut() {
  try { await api('/api/auth/logout', { method: 'POST' }) } catch { /* session may already be gone */ }
  clearSession()
  hideMessage($('#post-message'))
  load()
}

function render(posts) {
  feed.innerHTML = ''
  if (!posts.length) {
    feed.textContent = 'No posts found.'
    return
  }

  posts.forEach((post) => {
    const node = template.content.cloneNode(true)
    const message = node.querySelector('.post-message')
    node.querySelector('.author').textContent = `${post.author.name} @${post.author.username}`
    node.querySelector('time').textContent = new Date(post.createdAt).toLocaleString()
    node.querySelector('.content').textContent = post.content

    const like = node.querySelector('.like')
    like.textContent = post.liked ? `♥ Liked (${post.likes})` : `♡ Like (${post.likes})`
    like.setAttribute('aria-pressed', String(post.liked))
    like.classList.toggle('liked', post.liked)
    like.onclick = async () => {
      if (!state.user) return showMessage(message, 'Sign in to like posts.')
      try {
        await api(`/api/posts/${post.id}/like`, { method: 'POST' })
        load()
      } catch (error) { showMessage(message, error.message) }
    }

    post.comments.forEach((comment) => {
      const item = document.createElement('div')
      item.textContent = `@${comment.author.username}: ${comment.content}`
      node.querySelector('.comments').append(item)
    })

    const form = node.querySelector('.comment')
    if (state.user) {
      form.classList.remove('hidden')
      form.onsubmit = async (event) => {
        event.preventDefault()
        const content = String(new FormData(form).get('comment') || '').trim()
        if (!content) return showMessage(message, 'Write a comment before replying.')
        try {
          await api(`/api/posts/${post.id}/comments`, { method: 'POST', body: JSON.stringify({ content }) })
          load()
        } catch (error) { showMessage(message, error.message) }
      }
    } else {
      node.querySelector('.comment-hint').classList.remove('hidden')
    }
    feed.append(node)
  })
}

async function load() {
  try {
    const suffix = state.query ? `?q=${encodeURIComponent(state.query)}` : ''
    render((await api(`/api/posts${suffix}`)).posts)
  } catch (error) { feed.textContent = error.message }
  const status = $('#search-status')
  if (state.query) {
    $('#search-summary').textContent = `Showing results for “${state.query}”.`
    status.classList.remove('hidden')
  } else {
    status.classList.add('hidden')
  }
}

function credentials() {
  const values = Object.fromEntries(new FormData($('#auth')))
  return { username: String(values.username || '').trim(), password: String(values.password || '') }
}

// Field-specific validation: names exactly what is missing and marks the field invalid.
function missingCredentials({ username, password }) {
  $('#auth [name=username]').setAttribute('aria-invalid', String(!username))
  $('#auth [name=password]').setAttribute('aria-invalid', String(!password))
  if (!username && !password) return 'Enter your username and password.'
  if (!username) return 'Username is required.'
  if (!password) return 'Password is required.'
  return null
}

$('#auth').onsubmit = async (event) => {
  event.preventDefault()
  const { username, password } = credentials()
  const missing = missingCredentials({ username, password })
  if (missing) return showMessage($('#auth-message'), missing)
  try {
    signedIn(await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }))
  } catch (error) { showMessage($('#auth-message'), error.message) }
}

$('#register').onclick = async () => {
  const { username, password } = credentials()
  const missing = missingCredentials({ username, password })
  if (missing) return showMessage($('#auth-message'), missing)
  try {
    signedIn(await api('/api/auth/register', {
      method: 'POST', body: JSON.stringify({ username, password, name: username }),
    }))
  } catch (error) { showMessage($('#auth-message'), error.message) }
}

$('#logout').onclick = signOut
$('#account-logout').onclick = signOut

const postContent = $('#post-content')
postContent.oninput = () => { $('#char-count').textContent = `${postContent.value.length}/280` }

$('#new-post').onsubmit = async (event) => {
  event.preventDefault()
  const content = postContent.value.trim()
  if (!content) return showMessage($('#post-message'), 'Write something before publishing.')
  try {
    await api('/api/posts', { method: 'POST', body: JSON.stringify({ content }) })
    event.target.reset()
    $('#char-count').textContent = '0/280'
    showMessage($('#post-message'), 'Post published.', 'success')
    load()
  } catch (error) { showMessage($('#post-message'), error.message) }
}

$('#search').onsubmit = (event) => {
  event.preventDefault()
  const query = String(new FormData(event.target).get('q') || '').trim()
  if (!query) return showMessage($('#search-message'), 'Enter a search term to search posts.')
  hideMessage($('#search-message'))
  state.query = query
  load()
}

$('#clear-search').onclick = () => {
  state.query = ''
  $('#search').reset()
  hideMessage($('#search-message'))
  load()
}

async function initialize() {
  if (state.token) {
    try { setUser((await api('/api/auth/me')).user) } catch { clearSession() }
  }
  await load()
}

initialize()
