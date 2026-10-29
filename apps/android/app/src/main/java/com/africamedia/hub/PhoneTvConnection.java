package com.africamedia.hub;

import android.content.Context;
import java.io.*;
import java.math.BigInteger;
import java.security.*;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Date;
import java.util.concurrent.TimeUnit;
import io.github.muntashirakon.adb.AbsAdbConnectionManager;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;

/** A phone-local ADB identity; keys are never uploaded or included in backups. */
public final class PhoneTvConnection extends AbsAdbConnectionManager {
 private final PrivateKey key;
 private final Certificate certificate;
 public PhoneTvConnection(Context context) throws Exception {
  File folder=new File(context.getNoBackupFilesDir(),"tv-pairing");if(!folder.exists()&&!folder.mkdirs())throw new IOException("Cannot create phone pairing identity");
  File privateFile=new File(folder,"identity.pk8"),certFile=new File(folder,"identity.crt");
  if(privateFile.isFile()&&certFile.isFile()){
   key=KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(java.nio.file.Files.readAllBytes(privateFile.toPath())));
   try(InputStream in=new FileInputStream(certFile)){certificate=CertificateFactory.getInstance("X.509").generateCertificate(in);}
  }else{
   KeyPairGenerator generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);java.security.KeyPair pair=generator.generateKeyPair();key=pair.getPrivate();
   X500Name subject=new X500Name("CN=Africa Media Phone TV Installer");long now=System.currentTimeMillis();
   certificate=new JcaX509CertificateConverter().getCertificate(new JcaX509v3CertificateBuilder(subject,new BigInteger(120,new SecureRandom()),new Date(now-60000),new Date(now+10L*365*86400000),subject,pair.getPublic()).build(new JcaContentSignerBuilder("SHA256withRSA").build(key)));
   try(FileOutputStream out=new FileOutputStream(privateFile)){out.write(key.getEncoded());}
   try(FileOutputStream out=new FileOutputStream(certFile)){out.write(certificate.getEncoded());}
  }
  setApi(28);setTimeout(30,TimeUnit.SECONDS);
 }
 @Override protected PrivateKey getPrivateKey(){return key;}
 @Override protected Certificate getCertificate(){return certificate;}
 @Override protected String getDeviceName(){return "AfricaMediaPhone";}
}
