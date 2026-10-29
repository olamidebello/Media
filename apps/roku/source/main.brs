sub Main()
 screen = CreateObject("roSGScreen")
 port = CreateObject("roMessagePort")
 screen.SetMessagePort(port)
 screen.CreateScene("MainScene")
 screen.Show()
 while true
  message = wait(0, port)
  if type(message) = "roSGScreenEvent"
   if message.IsScreenClosed() then return
  end if
 end while
end sub
