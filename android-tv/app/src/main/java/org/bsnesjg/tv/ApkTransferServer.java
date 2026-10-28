package org.bsnesjg.tv;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;

/** Short-lived, token-protected LAN endpoint for a user-requested APK transfer. */
final class ApkTransferServer implements AutoCloseable {
    private static final long LIFETIME_MS = 10 * 60 * 1000L;
    private static final int MAX_DOWNLOADS = 5;
    private static final int MAX_LINE_BYTES = 4096;

    private final File apk;
    private final ServerSocket server;
    private final String token;
    private final String url;
    private final long expiresAt;
    private volatile boolean closed;
    private int downloads;
    private final Thread worker;

    static ApkTransferServer start(File apk) throws IOException {
        if (apk == null || !apk.isFile() || !apk.canRead()) throw new IOException("Installed APK unavailable");
        Inet4Address address = findLanAddress();
        ServerSocket socket = new ServerSocket();
        try {
            socket.setReuseAddress(false);
            socket.bind(new InetSocketAddress(address, 0), 4);
            socket.setSoTimeout(1000);
            return new ApkTransferServer(apk, socket, address.getHostAddress());
        } catch (IOException failure) {
            try { socket.close(); } catch (IOException ignored) {}
            throw failure;
        }
    }

    private ApkTransferServer(File apk, ServerSocket server, String host) {
        this.apk = apk;
        this.server = server;
        byte[] secret = new byte[16];
        new SecureRandom().nextBytes(secret);
        StringBuilder hex = new StringBuilder(secret.length * 2);
        for (byte value : secret) hex.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        token = hex.toString();
        url = "http://" + host + ":" + server.getLocalPort() + "/" + token + "/app.apk";
        expiresAt = System.currentTimeMillis() + LIFETIME_MS;
        worker = new Thread(this::serve, "bjg-apk-transfer");
        worker.setDaemon(true);
        worker.start();
    }

    String url() { return url; }

    private static Inet4Address findLanAddress() throws IOException {
        List<Inet4Address> candidates = new ArrayList<>();
        Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
        if (interfaces == null) throw new IOException("No network interface is available");
        for (NetworkInterface network : Collections.list(interfaces)) {
            String name = network.getName().toLowerCase(Locale.ROOT);
            if (!network.isUp() || network.isLoopback() || name.startsWith("tun") ||
                    name.startsWith("ppp") || name.startsWith("rmnet") || name.startsWith("dummy")) continue;
            Enumeration<java.net.InetAddress> addresses = network.getInetAddresses();
            while (addresses.hasMoreElements()) {
                java.net.InetAddress address = addresses.nextElement();
                if (address instanceof Inet4Address && address.isSiteLocalAddress()
                        && !address.isLoopbackAddress() && !address.isLinkLocalAddress()) {
                    candidates.add((Inet4Address) address);
                }
            }
        }
        if (candidates.isEmpty()) throw new IOException("Connect the TV and phone to the same Wi-Fi network");
        Collections.sort(candidates, (left, right) -> {
            int a = interfacePriority(left);
            int b = interfacePriority(right);
            return Integer.compare(a, b);
        });
        return candidates.get(0);
    }

    private static int interfacePriority(Inet4Address address) {
        try {
            NetworkInterface network = NetworkInterface.getByInetAddress(address);
            if (network == null) return 10;
            String name = network.getName().toLowerCase(Locale.ROOT);
            return name.startsWith("wlan") || name.startsWith("wifi") || name.startsWith("eth") ? 0 : 1;
        } catch (IOException ignored) {
            return 10;
        }
    }

    private void serve() {
        while (!closed && System.currentTimeMillis() < expiresAt && downloads < MAX_DOWNLOADS) {
            try (Socket client = server.accept()) {
                client.setSoTimeout(5000);
                handle(client);
            } catch (SocketTimeoutException waiting) {
                // Recheck the lifetime and user cancellation.
            } catch (IOException failure) {
                if (!closed) android.util.Log.w("BJG_APK_SHARE", "Local transfer request failed", failure);
            }
        }
        close();
    }

    private void handle(Socket client) throws IOException {
        BufferedInputStream input = new BufferedInputStream(client.getInputStream());
        String request = readLine(input);
        int headerCount = 0;
        String header;
        while ((header = readLine(input)) != null && !header.isEmpty() && ++headerCount < 64) {}
        String expected = "/" + token + "/app.apk";
        String[] parts = request == null ? new String[0] : request.split(" ", 3);
        if (parts.length != 3 || !("GET".equals(parts[0]) || "HEAD".equals(parts[0]))
                || !expected.equals(parts[1]) || System.currentTimeMillis() >= expiresAt) {
            writeResponse(client, 404, "Not Found", "text/plain", 0, null);
            return;
        }
        writeResponse(client, 200, "OK", "application/vnd.android.package-archive", apk.length(), filename());
        if ("HEAD".equals(parts[0])) return;
        try (FileInputStream file = new FileInputStream(apk);
             BufferedOutputStream output = new BufferedOutputStream(client.getOutputStream())) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = file.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
            output.flush();
            synchronized (this) { downloads++; }
        }
    }

    private String filename() {
        if (BuildConfig.NATIVE_ENGINE && BuildConfig.ROM_LIBRARY) return "bsnes-jg-native.apk";
        if (BuildConfig.NATIVE_ENGINE) return "mandelbrot-native.apk";
        if (BuildConfig.ROM_LIBRARY) return "bsnes-jg-wasm.apk";
        return "bsnes-jg-wasm-player.apk";
    }

    private static String readLine(BufferedInputStream input) throws IOException {
        StringBuilder line = new StringBuilder();
        int value;
        while ((value = input.read()) != -1) {
            if (value == '\n') break;
            if (value != '\r') {
                if (line.length() >= MAX_LINE_BYTES) throw new IOException("HTTP header line too long");
                line.append((char) value);
            }
        }
        if (value == -1 && line.length() == 0) return null;
        return line.toString();
    }

    private static void writeResponse(Socket client, int code, String reason, String mime,
                                      long length, String filename) throws IOException {
        BufferedOutputStream output = new BufferedOutputStream(client.getOutputStream());
        StringBuilder response = new StringBuilder()
                .append("HTTP/1.1 ").append(code).append(' ').append(reason).append("\r\n")
                .append("Content-Type: ").append(mime).append("\r\n")
                .append("Content-Length: ").append(length).append("\r\n")
                .append("Cache-Control: no-store\r\n")
                .append("Connection: close\r\n");
        if (filename != null) response.append("Content-Disposition: attachment; filename=\"")
                .append(filename).append("\"\r\n");
        response.append("\r\n");
        output.write(response.toString().getBytes(StandardCharsets.US_ASCII));
        output.flush();
    }

    @Override public void close() {
        if (closed) return;
        closed = true;
        try { server.close(); } catch (IOException ignored) {}
    }
}
