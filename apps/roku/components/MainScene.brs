sub init()
 m.list = m.top.findNode("channels")
 m.player = m.top.findNode("player")
 m.status = m.top.findNode("status")
 m.list.observeField("itemSelected", "playChannel")
 m.player.observeField("state", "playerState")
 m.task = CreateObject("roSGNode", "GuideTask")
 m.task.observeField("items", "guideReady")
 m.task.observeField("error", "guideError")
 m.task.control = "RUN"
 m.list.setFocus(true)
end sub
sub guideReady()
 content = CreateObject("roSGNode", "ContentNode")
 for each item in m.task.items
  node = content.createChild("ContentNode")
  node.title = item.title
  node.url = item.url
  node.streamFormat = item.streamformat
 end for
 m.list.content = content
 m.status.text = "Select a channel. Back returns to the guide."
end sub
sub guideError()
 m.status.text = m.task.error
end sub
sub playChannel()
 m.player.content = m.list.content.getChild(m.list.itemSelected)
 m.player.visible = true
 m.player.setFocus(true)
 m.player.control = "play"
end sub
sub closePlayer()
 m.player.control = "stop"
 m.player.visible = false
 m.list.setFocus(true)
end sub
sub playerState()
 if m.player.state = "error"
  closePlayer()
  m.status.text = "This stream cannot play on this TV. Try another channel."
 else if m.player.state = "finished"
  closePlayer()
 end if
end sub
function onKeyEvent(key as String, press as Boolean) as Boolean
 if press and key = "back" and m.player.visible
  closePlayer()
  return true
 end if
 return false
end function
