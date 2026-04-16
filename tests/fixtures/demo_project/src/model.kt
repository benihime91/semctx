// Data models.
// FEATURE: Demo Fixture.
package demo

data class Message(val body: String)

fun formatMessage(m: Message): String {
    return m.body
}
