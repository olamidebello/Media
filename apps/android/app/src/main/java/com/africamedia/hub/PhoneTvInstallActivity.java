package com.africamedia.hub;

import android.app.*;
import android.os.*;
import android.text.InputType;
import android.view.WindowManager;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.util.concurrent.*;
import io.github.muntashirakon.adb.AdbStream;

/** Native user-mediated pairing and installation of this app's own universal APK. */
public class PhoneTvInstallActivity extends Activity {
 private EditText host,connectPort,pairPort,code;
 private TextView status;
 private Button pair,install;
 private final ExecutorService worker=Executors.newSingleThreadExecutor();
 private final ScheduledExecutorService watchdog=Executors.newSingleThreadScheduledExecutor();
 private volatile PhoneTvConnection connection;
 private volatile boolean destroyed=false;
 @Override public void onCreate(Bundle state){super.onCreate(state);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(32,32,32,32);scroll.addView(layout);setContentView(scroll);
  TextView title=new TextView(this);title.setText("Pair phone with Android / Fire TV");title.setTextSize(24);layout.addView(title);
  TextView help=new TextView(this);help.setText("Connect this Android phone and TV to the same network (TV Ethernet is supported). On your TV enable Developer options → Wireless/network debugging. For pairing-code TVs open Pair device with pairing code. Enter the TV's address, pairing port and code below, then Pair phone. The connection port is shown on the main Wireless debugging screen and is usually different. For Fire TV/legacy network debugging, skip code pairing, use port 5555, and approve this phone on the TV. Samsung Tizen, LG webOS, Roku and Apple TV require other installation methods.");layout.addView(help);
  host=field(layout,"TV private IPv4 address","192.168.1.50",false);String initial=getIntent().getStringExtra("address");if(initial!=null)host.setText(initial);
  connectPort=field(layout,"TV debugging connection port","5555",true);pairPort=field(layout,"Pairing port (pairing-code TVs)","",true);code=field(layout,"Six-digit TV pairing code","",true);code.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_VARIATION_PASSWORD);
  pair=new Button(this);pair.setText("Pair phone using TV code");layout.addView(pair);install=new Button(this);install.setText("Connect, verify TV and install Africa Media Hub");layout.addView(install);status=new TextView(this);status.setText("Only connect to your own TV or a TV you are authorized to manage.");layout.addView(status);
  pair.setOnClickListener(v->{try{String ip=validateHost();int port=port(pairPort);String value=code.getText().toString().trim();if(!value.matches("[0-9]{6}"))throw new IllegalArgumentException("Enter the six-digit code displayed on the TV.");code.setText("");perform(()->{PhoneTvConnection manager=manager();say("Pairing with the TV…");if(!manager.pair(ip,port,value))throw new IOException("TV pairing failed");say("Phone paired. Enter the TV's debugging connection port, then choose Connect and install.");});}catch(Exception error){say(error.getMessage());}});
  install.setOnClickListener(v->{try{String ip=validateHost();int port=port(connectPort);new AlertDialog.Builder(this).setTitle("Install Africa Media Hub on "+ip+"?").setMessage("Approve the debugging connection on the TV. This copies the Africa Media Hub APK installed on this phone to a verified Android / Fire TV. Existing TV data is retained when Android allows the update.").setNegativeButton("Cancel",null).setPositiveButton("Verify and install",(dialog,which)->perform(()->installOnTV(ip,port))).show();}catch(Exception error){say(error.getMessage());}});
 }
 private EditText field(LinearLayout layout,String label,String hint,boolean numeric){TextView text=new TextView(this);text.setText(label);layout.addView(text);EditText input=new EditText(this);input.setSingleLine(true);input.setHint(hint);if(numeric)input.setInputType(InputType.TYPE_CLASS_NUMBER);layout.addView(input);return input;}
 private int port(EditText input){String text=input.getText().toString().trim();if(text.isEmpty()&&input==connectPort)text="5555";int value=Integer.parseInt(text);if(value<1||value>65535)throw new IllegalArgumentException("Port must be between 1 and 65535.");return value;}
 private String validateHost() throws Exception {String value=host.getText().toString().trim();if(!value.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))throw new IllegalArgumentException("Enter the TV's private IPv4 address.");String[] parts=value.split("\\.");for(String part:parts)if(Integer.parseInt(part)>255)throw new IllegalArgumentException("Invalid TV address.");int first=Integer.parseInt(parts[0]),second=Integer.parseInt(parts[1]);if(!(first==10||(first==192&&second==168)||(first==172&&second>=16&&second<=31)))throw new IllegalArgumentException("Use a private TV address on your local network.");return value;}
 private PhoneTvConnection manager() throws Exception {if(connection==null)connection=new PhoneTvConnection(getApplicationContext());return connection;}
 private void perform(Job job){pair.setEnabled(false);install.setEnabled(false);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);worker.execute(()->{ScheduledFuture<?> timeout=watchdog.schedule(()->{PhoneTvConnection current=connection;if(current!=null&&current.getAdbConnection()!=null)try{current.getAdbConnection().close();}catch(Exception ignored){}say("Connection timed out. Check TV approval, pairing and the connection port.");},180,TimeUnit.SECONDS);try{job.run();}catch(Exception error){say("Unable to complete: "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage())+". Check the TV approval prompt and debugging settings.");}finally{timeout.cancel(false);if(connection!=null)try{connection.disconnect();}catch(Exception ignored){}runOnUiThread(()->{if(!destroyed){pair.setEnabled(true);install.setEnabled(true);getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);}});}});}
 private String read(InputStream in,int limit) throws IOException {ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int count;while((count=in.read(buffer))!=-1){if(out.size()+count>limit)throw new IOException("Unexpected TV response size");out.write(buffer,0,count);}return out.toString("UTF-8");}
 private void installOnTV(String ip,int port) throws Exception {PhoneTvConnection manager=manager();say("Connecting. Approve this phone on the TV if prompted…");if(!manager.connect(ip,port))throw new IOException("TV connection was not established");String features;try(AdbStream stream=manager.openStream("shell:pm list features")){features=read(stream.openInputStream(),65536);}if(!features.contains("android.software.leanback")&&!features.contains("android.hardware.type.television"))throw new IOException("The connected device did not report Android TV support. Installation stopped");
  android.content.pm.ApplicationInfo app=getApplicationInfo();if(app.splitSourceDirs!=null&&app.splitSourceDirs.length>0)throw new IOException("Install the universal Africa Media Hub APK on this phone first; split APK transfer is not supported");File apk=new File(app.sourceDir);long size=apk.length();if(size<=0||size>200L*1024*1024)throw new IOException("Phone APK is unavailable or exceeds the transfer limit");say("TV verified. Sending the app from this phone…");
  try(AdbStream stream=manager.openStream("exec:cmd package install -r -S "+size);InputStream file=new FileInputStream(apk)){OutputStream out=stream.openOutputStream();byte[] buffer=new byte[32768];int count;long sent=0;while((count=file.read(buffer))!=-1){if(destroyed)throw new IOException("Installation cancelled");out.write(buffer,0,count);sent+=count;}out.flush();if(sent!=size)throw new IOException("Incomplete APK transfer");String result=read(stream.openInputStream(),65536);if(!result.contains("Success"))throw new IOException("TV rejected the APK: "+result.replaceAll("[\\r\\n]+"," ").substring(0,Math.min(result.replaceAll("[\\r\\n]+"," ").length(),300)));}
  say("Installation succeeded. Open Africa Media Hub on the TV. You can now turn off TV debugging if no longer needed.");
 }
 private void say(String message){runOnUiThread(()->{if(!destroyed)status.setText(message);});}
 @Override protected void onDestroy(){destroyed=true;worker.shutdownNow();watchdog.shutdownNow();PhoneTvConnection current=connection;if(current!=null){new Thread(()->{try{current.disconnect();}catch(Exception ignored){}}).start();}super.onDestroy();}
 private interface Job {void run() throws Exception;}
}
