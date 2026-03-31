import { reactive } from "vue"

const subscribed = reactive({})

export function useListUpdate(socket, doctype, callback) {
	subscribe(socket, doctype)
	socket.on("list_update", (data) => {
		if (data.doctype == doctype) {
			callback(data.name)
		}
	})
}

function subscribe(socket, doctype) {
	if (subscribed[doctype]) return

	socket.emit("doctype_subscribe", doctype)
	subscribed[doctype] = true

	// Re-subscribe after reconnect (server loses room state on disconnect)
	socket.on("connect", () => {
		socket.emit("doctype_subscribe", doctype)
	})
}
