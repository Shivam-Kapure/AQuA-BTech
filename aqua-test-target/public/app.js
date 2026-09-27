const state = { token: localStorage.getItem('circle-session'), user: null }
const feed = document.querySelector('#feed')
const template = document.querySelector('#post')

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

function clearSession() {
  state.user = null
  state.token = null
  localStorage.removeItem('circle-session')
  document.querySelector('#session').textContent = 'Guest mode'
  document.querySelector('#composer').classList.add('hidden')
}

function setUser(user) {
  state.user = user
  document.querySelector('#session').textContent = `@${user.username}`
  document.querySelector('#composer').classList.remove('hidden')
}

function signedIn(data) {
  state.token = data.token
  localStorage.setItem('circle-session', data.token)
  setUser(data.user)
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
    node.querySelector('.author').textContent = `${post.author.name} @${post.author.username}`
    node.querySelector('time').textContent = new Date(post.createdAt).toLocaleString()
    node.querySelector('.content').textContent = post.content
    node.querySelector('.like').textContent = `♡ Like (${post.likes})`
    post.comments.forEach((comment) => {
      const item = document.createElement('div')
      item.textContent = `@${comment.author.username}: ${comment.content}`
      node.querySelector('.comments').append(item)
    })
    node.querySelector('.like').onclick = async () => {
      try {
        await api(`/api/posts/${post.id}/like`, { method: 'POST' })
        load()
      } catch (error) { alert(error.message) }
    }
    const form = node.querySelector('.comment')
    if (state.token) {
      form.classList.remove('hidden')
      form.onsubmit = async (event) => {
        event.preventDefault()
        try {
          await api(`/api/posts/${post.id}/comments`, {
            method: 'POST', body: JSON.stringify({ content: new FormData(form).get('content') }),
          })
          load()
        } catch (error) { alert(error.message) }
      }
    }
    feed.append(node)
  })
}

async function load(query = '') {
  try {
    const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
    render((await api(`/api/posts${suffix}`)).posts)
  } catch (error) { feed.textContent = error.message }
}

document.querySelector('#auth').onsubmit = async (event) => {
  event.preventDefault()
  try {
    signedIn(await api('/api/auth/login', {
      method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(event.target))),
    }))
  } catch (error) { alert(error.message) }
}

document.querySelector('#register').onclick = async () => {
  const values = Object.fromEntries(new FormData(document.querySelector('#auth')))
  try {
    signedIn(await api('/api/auth/register', {
      method: 'POST', body: JSON.stringify({ ...values, name: values.username }),
    }))
  } catch (error) { alert(error.message) }
}

document.querySelector('#new-post').onsubmit = async (event) => {
  event.preventDefault()
  try {
    await api('/api/posts', {
      method: 'POST', body: JSON.stringify({ content: new FormData(event.target).get('content') }),
    })
    event.target.reset()
    load()
  } catch (error) { alert(error.message) }
}

document.querySelector('#search').onsubmit = (event) => {
  event.preventDefault()
  load(new FormData(event.target).get('q'))
}

async function initialize() {
  if (state.token) {
    try { setUser((await api('/api/auth/me')).user) } catch { clearSession() }
  }
  await load()
}

initialize()
