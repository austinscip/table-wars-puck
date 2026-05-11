// Single shared Socket.IO client. Same-origin connection (Flask serves
// both the bundle and Socket.IO on the same host), so we don't pass a
// URL — socket.io-client defaults to window.location.origin.

import { io, type Socket } from 'socket.io-client'

let _socket: Socket | null = null

export function getSocket(): Socket {
  if (_socket) return _socket
  _socket = io({
    autoConnect: true,
    reconnection: true,
    transports: ['websocket', 'polling'],
  })
  return _socket
}
