sub init()
 m.top.functionName = "loadGuide"
end sub
sub loadGuide()
 request = CreateObject("roUrlTransfer")
 request.SetCertificatesFile("common:/certs/ca-bundle.crt")
 request.InitClientCertificates()
 request.SetUrl("https://media.africandroid.world/api/guide")
 port = CreateObject("roMessagePort")
 request.SetPort(port)
 request.AsyncGetToString()
 message = wait(15000, port)
 if message = invalid
  request.AsyncCancel()
  m.top.error = "Guide timed out. Reopen the app to retry."
  return
 end if
 if message.GetResponseCode() <> 200
  m.top.error = "Channel guide unavailable."
  return
 end if
 data = ParseJson(message.GetString())
 items = []
 if type(data) = "roAssociativeArray"
  if type(data.channels) = "roArray"
   for each channel in data.channels
    if type(channel.url) = "roString" and type(channel.name) = "roString"
     url = LCase(channel.url)
     format = ""
     if Instr(1, url, ".m3u8") > 0 then format = "hls"
     if Instr(1, url, ".mp4") > 0 then format = "mp4"
     if Left(url, 8) = "https://" and format <> ""
      items.Push({title:channel.name, url:channel.url, streamformat:format})
     end if
    end if
   end for
  end if
 end if
 if items.Count() = 0
  m.top.error = "No compatible HTTPS HLS or MP4 channels available."
 else
  m.top.items = items
 end if
end sub
