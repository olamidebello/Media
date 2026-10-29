package com.africamedia.hub;
import android.app.*;
import android.os.*;
import android.content.Intent;
import android.widget.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class CameraDevicesActivity extends Activity {
 private volatile boolean stopped=false;
 private volatile DatagramSocket socket;
 private android.net.wifi.WifiManager.MulticastLock multicast;
 private LinearLayout rows;
 private TextView status;
 private final Set<String> found=new HashSet<>();
 private boolean local(InetAddress address){if(!(address instanceof Inet4Address))return false;byte[] a=address.getAddress();int x=a[0]&255,y=a[1]&255;return x==10||(x==192&&y==168)||(x==172&&y>=16&&y<=31);}
 @Override public void onCreate(Bundle state){super.onCreate(state);ScrollView scroll=new ScrollView(this);rows=new LinearLayout(this);rows.setOrientation(LinearLayout.VERTICAL);rows.setPadding(32,32,32,32);scroll.addView(rows);setContentView(scroll);TextView title=new TextView(this);title.setText("My Streaming · Find cameras");title.setTextSize(24);rows.addView(title);status=new TextView(this);status.setText("Searching this Wi-Fi for ONVIF cameras. Select only a camera you own or are authorized to view. Camera authentication and gateway setup are still required.");rows.addView(status);
 try{android.net.wifi.WifiManager wifi=(android.net.wifi.WifiManager)getApplicationContext().getSystemService(WIFI_SERVICE);multicast=wifi.createMulticastLock("MediaCameraDiscovery");multicast.setReferenceCounted(false);multicast.acquire();}catch(RuntimeException ignored){}
 new Thread(this::discover,"MediaCameraDiscovery").start();}
 private void discover(){try(DatagramSocket active=new DatagramSocket()){socket=active;if(stopped)return;active.setSoTimeout(1000);String probe="<?xml version=\"1.0\"?><e:Envelope xmlns:e=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:w=\"http://schemas.xmlsoap.org/ws/2004/08/addressing\" xmlns:d=\"http://schemas.xmlsoap.org/ws/2005/04/discovery\" xmlns:n=\"http://www.onvif.org/ver10/network/wsdl\"><e:Header><w:MessageID>uuid:"+UUID.randomUUID()+"</w:MessageID><w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To><w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header><e:Body><d:Probe><d:Types>n:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>";byte[] data=probe.getBytes(StandardCharsets.UTF_8);active.send(new DatagramPacket(data,data.length,InetAddress.getByName("239.255.255.250"),3702));long until=System.currentTimeMillis()+8000;int packets=0;while(!stopped&&System.currentTimeMillis()<until&&packets<128){DatagramPacket packet=new DatagramPacket(new byte[65536],65536);try{active.receive(packet);}catch(SocketTimeoutException timeout){continue;}packets++;if(!local(packet.getAddress()))continue;String xml=new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8);if(!xml.contains("ProbeMatch")||xml.contains("<!DOCTYPE")||xml.contains("<!ENTITY"))continue;String address=packet.getAddress().getHostAddress();if(!found.add(address))continue;String name="Network camera";java.util.regex.Matcher match=java.util.regex.Pattern.compile("onvif://www\\.onvif\\.org/name/([^\\s<]+)").matcher(xml);if(match.find())try{name=URLDecoder.decode(match.group(1),"UTF-8");}catch(Exception ignored){}final String label=name.length()>100?name.substring(0,100):name;runOnUiThread(()->{if(stopped)return;Button button=new Button(this);button.setText(label+" ("+address+")");button.setOnClickListener(v->{setResult(RESULT_OK,new Intent().putExtra("name",label).putExtra("address",address));finish();});rows.addView(button);});}runOnUiThread(()->status.setText(found.isEmpty()?"No advertised cameras found. Check Wi-Fi isolation, ONVIF settings and permissions, or add the camera manually.":"Select a camera, then confirm Add to my profile. Pair a gateway for remote viewing."));}catch(Exception error){runOnUiThread(()->status.setText("Camera discovery unavailable. Check Wi-Fi and permissions, or add the camera manually."));}finally{socket=null;if(multicast!=null&&multicast.isHeld())multicast.release();}}
 @Override protected void onDestroy(){stopped=true;if(socket!=null)socket.close();super.onDestroy();}
}
