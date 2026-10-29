package com.africamedia.hub;

import android.app.*;
import android.os.*;
import android.net.nsd.*;
import android.content.Intent;
import android.net.Uri;
import android.widget.*;
import java.net.*;
import java.util.*;

/** Local discovery remains on the phone. No discovered addresses are sent to the server. */
public class TvDevicesActivity extends Activity {
 private NsdManager manager;
 private android.net.wifi.WifiManager.MulticastLock multicast;
 private final ArrayList<NsdManager.DiscoveryListener> listeners=new ArrayList<>();
 private final Set<String> seen=new HashSet<>();
 private final ArrayDeque<NsdServiceInfo> pending=new ArrayDeque<>();
 private boolean resolving=false;
 private volatile boolean stopped=false;
 private volatile DatagramSocket ssdpSocket;
 private LinearLayout rows;
 private TextView status;
 private final Handler handler=new Handler(Looper.getMainLooper());
 private final String[][] services={{"_googlecast._tcp.","android"},{"_androidtvremote2._tcp.","android"},{"_adb-tls-connect._tcp.","android"},{"_airplay._tcp.","apple"},{"_raop._tcp.","apple"},{"_webostv._tcp.","lg"},{"_roku-ecp._tcp.","roku"}};
 @Override public void onCreate(Bundle state){super.onCreate(state);manager=(NsdManager)getSystemService(NSD_SERVICE);ScrollView scroll=new ScrollView(this);rows=new LinearLayout(this);rows.setOrientation(LinearLayout.VERTICAL);rows.setPadding(32,32,32,32);scroll.addView(rows);setContentView(scroll);
 TextView title=new TextView(this);title.setText("Install on a nearby TV");title.setTextSize(24);rows.addView(title);
 status=new TextView(this);status.setText("Connect your phone and TV to the same Wi-Fi. Searching for advertised TV services… Cast and AirPlay receivers may be accessories rather than installable TVs. Select a device to confirm its operating system and see installation options.");rows.addView(status);
 try{android.net.wifi.WifiManager wifi=(android.net.wifi.WifiManager)getApplicationContext().getSystemService(WIFI_SERVICE);multicast=wifi.createMulticastLock("AfricaMediaTVDiscovery");multicast.setReferenceCounted(false);multicast.acquire();}catch(RuntimeException ignored){}
 for(String[] service:services)discover(service[0],service[1]);
 new Thread(this::discoverSsdp,"TV-SSDP-discovery").start();
 handler.postDelayed(()->{stopDiscovery();status.setText(seen.isEmpty()?"No compatible services found. Check Wi-Fi, TV power and network permissions. Some TVs do not advertise discovery services. Use manual platform selection on the install page.":"Search complete. Select a device below. The platform estimate can be corrected on the installation page.");},12000);
 }
 private boolean local(InetAddress address){if(!(address instanceof Inet4Address))return false;byte[] a=address.getAddress();int first=a[0]&255,second=a[1]&255;return first==10||(first==192&&second==168)||(first==172&&second>=16&&second<=31);}
 private void discover(String type,String platform){NsdManager.DiscoveryListener listener=new NsdManager.DiscoveryListener(){
  public void onDiscoveryStarted(String t){}
  public void onServiceFound(NsdServiceInfo info){runOnUiThread(()->{if(stopped)return;pending.add(info);resolveNext();});}
  public void onServiceLost(NsdServiceInfo info){}
  public void onDiscoveryStopped(String t){}
  public void onStartDiscoveryFailed(String t,int code){runOnUiThread(()->status.setText("Some discovery services are unavailable. Check local network permissions and Wi-Fi. Manual platform selection is available on the install page."));}
  public void onStopDiscoveryFailed(String t,int code){}
 };listeners.add(listener);try{manager.discoverServices(type,NsdManager.PROTOCOL_DNS_SD,listener);}catch(RuntimeException error){status.setText("Discovery permission unavailable. Use manual platform selection on the install page.");}}
 private void resolveNext(){if(stopped||resolving||pending.isEmpty())return;resolving=true;NsdServiceInfo service=pending.remove();try{manager.resolveService(service,new NsdManager.ResolveListener(){
  public void onResolveFailed(NsdServiceInfo info,int code){runOnUiThread(()->{resolving=false;resolveNext();});}
  public void onServiceResolved(NsdServiceInfo info){runOnUiThread(()->{resolving=false;if(!stopped&&info.getHost()!=null&&local(info.getHost()))addDevice(info);resolveNext();});}
 });}catch(RuntimeException error){resolving=false;resolveNext();}}
 private void addDevice(NsdServiceInfo info){String address=info.getHost().getHostAddress();String type=info.getServiceType();String platform="browser";for(String[] item:services)if(type.replace(".","").equals(item[0].replace(".","")))platform=item[1];String name=info.getServiceName();if(name.toLowerCase(Locale.ROOT).contains("firetv"))platform="fire";
 String key=address+":"+platform;if(!seen.add(key))return;Button button=new Button(this);button.setText(name+" — "+platform+" ("+address+")");final String selected=platform;
 button.setOnClickListener(v->new AlertDialog.Builder(this).setTitle(name).setMessage("Open installation options for "+selected+"? Discovery identifies an advertised service and may not identify the TV operating system exactly. Confirm the platform on the next screen. Installation may require developer mode, a paired computer, or the TV's app store; this phone does not bypass TV approval.").setNegativeButton("Cancel",null).setPositiveButton("Installation options",(dialog,which)->{setResult(RESULT_OK,new Intent().putExtra("platform",selected));finish();}).show());rows.addView(button);
 }
 private void discoverSsdp(){try(DatagramSocket socket=new DatagramSocket()){ssdpSocket=socket;if(stopped)return;socket.setSoTimeout(1000);String query="M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n";byte[] payload=query.getBytes(java.nio.charset.StandardCharsets.US_ASCII);socket.send(new DatagramPacket(payload,payload.length,InetAddress.getByName("239.255.255.250"),1900));long until=System.currentTimeMillis()+8000;int count=0;while(!stopped&&System.currentTimeMillis()<until&&count<64){byte[] data=new byte[8192];DatagramPacket packet=new DatagramPacket(data,data.length);try{socket.receive(packet);}catch(SocketTimeoutException timeout){continue;}count++;if(!local(packet.getAddress()))continue;String text=new String(data,0,packet.getLength(),java.nio.charset.StandardCharsets.UTF_8);String lower=text.toLowerCase(Locale.ROOT);String platform=lower.contains("roku")?"roku":lower.contains("tizen")?"samsung":lower.contains("webos")?"lg":lower.contains("firetv")||lower.contains("fire tv")?"fire":"browser";if(platform.equals("browser")&&!lower.contains("mediarenderer"))continue;String address=packet.getAddress().getHostAddress();final String selected=platform;runOnUiThread(()->{if(stopped||seen.size()>=32||!seen.add(address+":"+selected))return;Button button=new Button(this);button.setText("Network TV — "+selected+" ("+address+")");button.setOnClickListener(v->new AlertDialog.Builder(this).setTitle("TV platform detected: "+selected).setMessage("Confirm the TV operating system on the installation page. TV approval or a paired computer may be needed.").setNegativeButton("Cancel",null).setPositiveButton("Installation options",(dialog,which)->{setResult(RESULT_OK,new Intent().putExtra("platform",selected));finish();}).show());rows.addView(button);});}}catch(Exception ignored){}finally{ssdpSocket=null;}}
 private void stopDiscovery(){if(stopped)return;stopped=true;if(ssdpSocket!=null)ssdpSocket.close();for(NsdManager.DiscoveryListener listener:listeners)try{manager.stopServiceDiscovery(listener);}catch(RuntimeException ignored){}listeners.clear();pending.clear();if(multicast!=null&&multicast.isHeld())multicast.release();}
 @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);stopDiscovery();super.onDestroy();}
}
