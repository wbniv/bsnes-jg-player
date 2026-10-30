import org.gradle.api.tasks.Sync
import java.io.FileInputStream
import java.security.MessageDigest
import java.security.KeyStore
import java.util.zip.ZipFile

plugins {
    id("com.android.application")
}

dependencies {
    implementation(files("libs/zxing-core-3.5.4.jar"))
}

val tvProject = rootProject.projectDir
val repo = tvProject.parentFile
val playerRomConfig = groovy.json.JsonSlurper().parse(repo.resolve("demo-rom.json")) as Map<*, *>
val playerRomSlug = playerRomConfig["slug"] as String
val playerRomTitle = playerRomConfig["title"] as String
val playerRomApkSlug = playerRomConfig["apkSlug"] as String
val playerRomSha = playerRomConfig["sha256"] as String
val playerRomSelfCheck = groovy.json.JsonOutput.toJson(playerRomConfig["selfcheck"] ?: emptyMap<String, Any>())
val rom = tvProject.resolve("fixture/mandel-display.sfc")
val map = tvProject.resolve("fixture/mandel-display.map")
val referenceFrame = tvProject.resolve("fixture/reference-5800.png")
val qrLibrary = tvProject.resolve("app/libs/zxing-core-3.5.4.jar")
val expectedQrLibrarySha = "71de5d89341b5fcf5dd89da7f44e84d825d0e084cdf3ec77c9abe26b0f0ceb13"
val expectedRomSha = "6c13c9042ca68be06f42650862ad7e116cc782e3a433ceaf9f760f090b430353"
val expectedMapSha = "44ebc8e330f5e70c5723ff90b80e1a55fb53b914c6a4d4d1dc970a933b27c3cb"
val expectedReferenceSha = "7acaa3825b82b7e61fe641ca950508d58e8aeb0cb2ff7849547d17eacaab4abe"
val expectedGlueSha = "54e19fd849b823d87e278438fe7ec5ccaf8e526e966c8f4e007d29ccf78cdf4d"
val expectedWasmSha = "e74dbd3d7160608dfb6e1ae2ed7ff263fafaa62b0444870530530e2e931ebeb3"
val controlledDebugSigning = providers.gradleProperty("controlledDebugSigning")
    .map(String::toBoolean).getOrElse(false)
val releaseKeystorePath = providers.environmentVariable("BJG_RELEASE_KEYSTORE").orNull
val releaseKeystorePassword = providers.environmentVariable("BJG_RELEASE_KEYSTORE_PASSWORD").orNull
val releaseKeyAlias = providers.environmentVariable("BJG_RELEASE_KEY_ALIAS").orNull
val releaseKeyPassword = providers.environmentVariable("BJG_RELEASE_KEY_PASSWORD").orNull
val releaseSigningConfigured = !releaseKeystorePath.isNullOrBlank() &&
    !releaseKeystorePassword.isNullOrBlank() && !releaseKeyAlias.isNullOrBlank() &&
    !releaseKeyPassword.isNullOrBlank() && releaseKeystorePath?.let { file(it).isFile } == true
val nativeAssetsDir = layout.buildDirectory.dir("generated/nativeAssets")
val nativePlayerAssetsDir = layout.buildDirectory.dir("generated/nativePlayerAssets")
val publishedLibraryDir = layout.buildDirectory.dir("generated/publishedLibrary")
val publishedAssetsDir = layout.buildDirectory.dir("generated/publishedAssets")
val wasmAssetsDir = layout.buildDirectory.dir("generated/wasmAssets")
val stagePublishedLibrary by tasks.registering {
    outputs.dir(publishedLibraryDir)
    outputs.upToDateWhen { false }
    doLast { check(publishedLibraryDir.get().file("library.json").asFile.isFile) { "Run sync-published-library.py before the container build" } }
}
val stagePublishedAssets by tasks.registering(Sync::class) {
    dependsOn("verifyRomFixture", stagePublishedLibrary)
    into(publishedAssetsDir)
    from(tvProject.resolve("fixture/manifest.json")) { into("roms"); rename { "manifest.json" } }
    from(publishedLibraryDir) { into("roms"); include("*.sfc", "library.json", "cards/**") }
}
val stageNativeAssets by tasks.registering(Sync::class) {
    dependsOn(stagePublishedAssets)
    into(nativeAssetsDir)
    from(publishedAssetsDir)
    from(tvProject.resolve("fixture/reference-5800.png")) { rename { "reference-5800.png" } }
    from(repo.resolve("vendor/bsnes-jg/Database")) { into("Database") }
}
val stageNativePlayerAssets by tasks.registering(Sync::class) {
    dependsOn(verifyPlayerDemoRom)
    into(nativePlayerAssetsDir)
    from(repo.resolve("web/roms/$playerRomSlug.sfc")) { into("roms") }
    from(repo.resolve("vendor/bsnes-jg/Database")) {
        into("Database")
        include("boards.bml", "SuperFamicom.bml")
    }
}

val verifyPlayerDemoRom by tasks.registering {
    val sampleRom = repo.resolve("web/roms/$playerRomSlug.sfc")
    inputs.file(sampleRom)
    doLast {
        val actual = MessageDigest.getInstance("SHA-256").digest(sampleRom.readBytes())
            .joinToString("") { "%02x".format(it) }
        check(actual == playerRomSha) {
            "${playerRomTitle} sample ROM differs from its pinned published build"
        }
    }
}

val verifyRomFixture by tasks.registering {
    inputs.files(rom, map, referenceFrame)
    doLast {
        fun sha(file: java.io.File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes())
            .joinToString("") { "%02x".format(it) }
        check(sha(rom) == expectedRomSha) {
            "Frozen mandel-display ROM hash changed. Refresh fixture and oracle together."
        }
        check(sha(map) == expectedMapSha) {
            "Frozen mandel-display map hash changed. Refresh fixture and oracle together."
        }
        check(sha(referenceFrame) == expectedReferenceSha) {
            "Reference frame hash changed. Regenerate it with the pinned native gate and review it."
        }
        check(sha(repo.resolve("dist/engine/cores/bsnes_jg.js")) == expectedGlueSha) {
            "Pinned bsnes-jg glue changed. Refresh the validated core pair and provenance together."
        }
        check(sha(repo.resolve("dist/engine/cores/bsnes_jg.wasm")) == expectedWasmSha) {
            "Pinned bsnes-jg wasm changed. Refresh the validated core pair and provenance together."
        }
        val provenance = repo.resolve("dist/engine/cores/PROVENANCE.json").readText()
        check(provenance.contains("\"version\": \"2.1.0\"") &&
              provenance.contains("fe5be6afdff43ad58860d821fcc8572a23f92d19")) {
            "Pinned core provenance is missing or does not match the validated build."
        }
        check(tvProject.resolve("fixture/manifest.json").readText().contains("\"off\": \"0x580\"")) {
            "ROM self-check offset no longer matches the pinned map."
        }
        val fixtureManifest = tvProject.resolve("fixture/manifest.json").readText()
        check(fixtureManifest.contains("\"want\": \"0x204F\"") &&
              fixtureManifest.contains("\"frames\": 5800") &&
              fixtureManifest.contains(expectedReferenceSha)) {
            "Fixture manifest does not match the pinned WRAM oracle and reference frame."
        }
    }
}

val verifyQrLibrary by tasks.registering {
    inputs.file(qrLibrary)
    doLast {
        val actual = MessageDigest.getInstance("SHA-256").digest(qrLibrary.readBytes())
            .joinToString("") { "%02x".format(it) }
        check(actual == expectedQrLibrarySha) { "Vendored ZXing QR library hash changed" }
    }
}
tasks.named("preBuild") { dependsOn(verifyQrLibrary) }

val verifyPublicReleaseSigning by tasks.registering {
    group = "verification"
    description = "Requires the configured durable signing key for public APK releases."
    doLast {
        check(!controlledDebugSigning) {
            "Public release builds cannot use controlledDebugSigning"
        }
        check(releaseSigningConfigured) {
            "Set BJG_RELEASE_KEYSTORE, BJG_RELEASE_KEYSTORE_PASSWORD, " +
                "BJG_RELEASE_KEY_ALIAS, and BJG_RELEASE_KEY_PASSWORD to sign public APKs"
        }
        val releaseStore = KeyStore.getInstance("PKCS12")
        FileInputStream(releaseKeystorePath!!).use {
            releaseStore.load(it, releaseKeystorePassword!!.toCharArray())
        }
        val releaseCertificate = releaseStore.getCertificate(releaseKeyAlias!!)
            ?: error("The configured release alias has no certificate")
        val debugStore = KeyStore.getInstance("JKS")
        FileInputStream("/root/.android/debug.keystore").use {
            debugStore.load(it, "android".toCharArray())
        }
        val debugCertificate = debugStore.getCertificate("androiddebugkey")
            ?: error("The local debug keystore has no debug certificate")
        fun fingerprint(certificate: java.security.cert.Certificate) =
            MessageDigest.getInstance("SHA-256").digest(certificate.encoded)
                .joinToString("") { "%02x".format(it) }
        check(fingerprint(releaseCertificate) != fingerprint(debugCertificate)) {
            "The public release keystore uses the controlled-build debug certificate"
        }
    }
}
if (!controlledDebugSigning) {
    tasks.matching {
        it.name.startsWith("assemble") && it.name.endsWith("Release") &&
            (it.name.contains("Native") || it.name.contains("Nativeplayer"))
    }.configureEach { dependsOn(verifyPublicReleaseSigning) }
}

val stageWasmAssets by tasks.registering(Sync::class) {
    dependsOn(verifyRomFixture, stagePublishedAssets)
    into(wasmAssetsDir)
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(repo.resolve("web/app.js"))
    from(repo.resolve("dist/engine/cores")) {
        into("cores")
        include("bsnes_jg.js", "bsnes_jg.wasm", "PROVENANCE.json")
    }
    from(publishedAssetsDir)
}

android {
    namespace = "org.bsnesjg.tv"
    compileSdk = 34
    buildFeatures { buildConfig = true }

    defaultConfig {
        applicationId = "org.bsnesjg.tv"
        minSdk = 24
        targetSdk = 34
        versionCode = 10
        versionName = "0.1.9"
        buildConfigField("String", "PLAYER_ROM_SLUG", groovy.json.JsonOutput.toJson(playerRomSlug))
        buildConfigField("String", "PLAYER_ROM_TITLE", groovy.json.JsonOutput.toJson(playerRomTitle))
        buildConfigField("String", "PLAYER_ROM_APK_SLUG", groovy.json.JsonOutput.toJson(playerRomApkSlug))
        buildConfigField("String", "PLAYER_ROM_SHA256", groovy.json.JsonOutput.toJson(playerRomSha))
        buildConfigField("String", "PLAYER_ROM_SELFCHECK", groovy.json.JsonOutput.toJson(playerRomSelfCheck))
        // Set only after the public release page has been published and verified.
        val publicDownloadUrl = providers.gradleProperty("publicDownloadUrl").orElse("").get()
            .replace("\\", "\\\\").replace("\"", "\\\"")
        check(publicDownloadUrl.isEmpty() ||
                publicDownloadUrl.startsWith("https://downloads.biohack.net/bsnes-jg/")) {
            "publicDownloadUrl must use the verified Biohack SNES release page"
        }
        buildConfigField("String", "PUBLIC_DOWNLOAD_URL", "\"$publicDownloadUrl\"")
        ndkVersion = "26.2.11394342"
        externalNativeBuild {
            cmake { cppFlags += listOf("-std=c++11", "-O3") }
        }
        ndk { abiFilters += listOf("armeabi-v7a", "arm64-v8a") }
    }

    flavorDimensions += "engine"
    productFlavors {
        create("wasmplayer") {
            dimension = "engine"
            // Keep the original Phase 1 package and launcher identity.
            resValue("string", "app_name", "bsnes-jg")
            buildConfigField("boolean", "NATIVE_ENGINE", "false")
            buildConfigField("boolean", "ROM_LIBRARY", "false")
        }
        create("wasm") {
            dimension = "engine"
            // Keep Phase 2 measurements beside the Phase 1 install and user data.
            applicationIdSuffix = ".phase2"
            resValue("string", "app_name", "LLVM 65816 Torture Test Suite on SNES")
            buildConfigField("boolean", "NATIVE_ENGINE", "false")
            buildConfigField("boolean", "ROM_LIBRARY", "true")
        }
        create("native") {
            dimension = "engine"
            applicationIdSuffix = ".native.phase2"
            resValue("string", "app_name", "LLVM 65816 Torture Test Suite on SNES")
            buildConfigField("boolean", "NATIVE_ENGINE", "true")
            buildConfigField("boolean", "ROM_LIBRARY", "true")
        }
        create("nativeplayer") {
            dimension = "engine"
            applicationIdSuffix = ".native"
            resValue("string", "app_name", "$playerRomTitle Native")
            buildConfigField("boolean", "NATIVE_ENGINE", "true")
            buildConfigField("boolean", "ROM_LIBRARY", "false")
        }
    }

    buildTypes {
        getByName("release") {
            // Device test builds may opt into the local debug key. Public release
            // artifacts use the durable key supplied through the environment.
            signingConfig = when {
                controlledDebugSigning -> signingConfigs.getByName("debug")
                releaseSigningConfigured -> signingConfigs.create("publicRelease").apply {
                    storeFile = file(releaseKeystorePath!!)
                    storePassword = releaseKeystorePassword!!
                    keyAlias = releaseKeyAlias!!
                    keyPassword = releaseKeyPassword!!
                    storeType = "PKCS12"
                }
                else -> null
            }
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    sourceSets.getByName("wasm").assets.srcDir(stageWasmAssets.map { it.destinationDir })
    sourceSets.getByName("wasmplayer").assets.srcDir(stageWasmAssets.map { it.destinationDir })
    sourceSets.getByName("wasmplayer").assets.srcDir(tvProject.resolve("app/src/wasm/assets"))
    sourceSets.getByName("native").assets.srcDir(nativeAssetsDir)
    sourceSets.getByName("nativeplayer").assets.srcDir(nativePlayerAssetsDir)
    sourceSets.getByName("nativeplayer").assets.srcDir(tvProject.resolve("app/src/native/assets"))
    externalNativeBuild { cmake { path = file("src/main/cpp/CMakeLists.txt"); version = "3.22.1" } }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

stageNativeAssets.configure { dependsOn(verifyRomFixture) }
tasks.configureEach {
    when (name) {
        "preWasmplayerDebugBuild", "preWasmplayerReleaseBuild" -> dependsOn(stageWasmAssets)
        "preWasmDebugBuild", "preWasmReleaseBuild" -> dependsOn(stageWasmAssets)
        "preNativeDebugBuild", "preNativeReleaseBuild" -> dependsOn(stageNativeAssets)
        "preNativeplayerDebugBuild", "preNativeplayerReleaseBuild" -> dependsOn(stageNativePlayerAssets)
    }
}

fun verifyApkArtifact(taskName: String, variant: String) = tasks.register(taskName) {
    val buildType = if (variant.endsWith("Debug")) "Debug" else if (variant.endsWith("Release")) "Release" else error("Bad variant: $variant")
    val flavor = variant.removeSuffix(buildType).lowercase()
    dependsOn("assemble$variant")
    val apk = layout.buildDirectory.file("outputs/apk/$flavor/${buildType.lowercase()}/app-$flavor-${buildType.lowercase()}.apk")
    inputs.file(apk)
    doLast {
        val file = apk.get().asFile
        val required = mutableSetOf(
            "AndroidManifest.xml", "classes.dex", "assets/index.html", "assets/library.js", "assets/library.css",
            "assets/tv.js", "assets/tv-player.js", "assets/tv-scheduler.js", "assets/performance-overlay.js",
            "assets/performance-overlay.css", "assets/engine-adapter.js", "assets/apk-share-menu.js"
        )
        if (flavor != "nativeplayer") {
            required += setOf("assets/roms/library.json", "assets/roms/manifest.json")
        }
        if (flavor == "wasm" || flavor == "wasmplayer") {
            required += setOf("assets/app.js", "assets/cores/bsnes_jg.js", "assets/cores/bsnes_jg.wasm", "assets/cores/PROVENANCE.json")
        } else {
            required += setOf("lib/armeabi-v7a/libbjg.so", "lib/arm64-v8a/libbjg.so", "assets/Database/boards.bml",
                "assets/Database/SuperFamicom.bml")
            if (flavor != "nativeplayer") required += "assets/reference-5800.png"
        }
        if (flavor == "nativeplayer") required += "assets/roms/$playerRomSlug.sfc"
        fun sha(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        ZipFile(file).use { zip ->
            val entries = zip.entries().asSequence().filterNot { it.isDirectory }.map { it.name }.toSet()
            check(entries.containsAll(required)) { "APK is missing assets: ${required - entries}" }
            val romEntries = entries.filter { it.startsWith("assets/roms/") && it.endsWith(".sfc") }
            if (flavor == "nativeplayer") {
                check(romEntries == listOf("assets/roms/$playerRomSlug.sfc")) {
                    "Standalone Native player must contain only the configured demo ROM"
                }
                check(sha(zip.getInputStream(zip.getEntry("assets/roms/$playerRomSlug.sfc")).use { it.readBytes() }) == playerRomSha) {
                    "Standalone Native player ROM differs from the configured published build"
                }
                check(entries.none { it.startsWith("assets/roms/cards/") || it == "assets/roms/library.json" || it == "assets/roms/manifest.json" }) {
                    "Standalone Native player must not package the full ROM library or card art"
                }
            } else {
                val library = groovy.json.JsonSlurper().parseText(
                    zip.getInputStream(zip.getEntry("assets/roms/library.json")).bufferedReader().use { it.readText() }
                ) as Map<*, *>
                val records = library["roms"] as List<*>
                val ids = records.map { (it as Map<*, *>) ["slug"] as String }.toSet()
                check(records.size == 152 && ids.size == 152) { "Expected 152 unique catalog records" }
                check(romEntries.size == 152 && romEntries.map { it.substringAfterLast('/').removeSuffix(".sfc") }.toSet() == ids) {
                    "APK ROM files do not exactly match the published catalog"
                }
                val cards = entries.filter { it.startsWith("assets/roms/cards/") && it.endsWith(".png") }
                check(cards.size == 152 && cards.map { it.substringAfterLast('/').removeSuffix(".png") }.toSet() == ids) {
                    "APK card art does not exactly match the published catalog"
                }
                records.forEach { raw ->
                    val record = raw as Map<*, *>
                    val id = record["slug"] as String
                    val romEntry = zip.getEntry("assets/roms/$id.sfc")
                    val cardEntry = zip.getEntry("assets/roms/cards/$id.png")
                    check(romEntry.size == (record["size"] as Number).toLong()) { "ROM size mismatch for $id" }
                    check(sha(zip.getInputStream(romEntry).use { it.readBytes() }) == record["romSha256"]) { "ROM hash mismatch for $id" }
                    check(sha(zip.getInputStream(cardEntry).use { it.readBytes() }) == record["cardSha256"]) { "Card hash mismatch for $id" }
                }
            }
            if (flavor == "wasm" || flavor == "wasmplayer") {
                check(sha(zip.getInputStream(zip.getEntry("assets/app.js")).use { it.readBytes() }) == sha(repo.resolve("web/app.js").readBytes())) {
                    "APK player does not match the canonical web/app.js source"
                }
                check(sha(zip.getInputStream(zip.getEntry("assets/cores/bsnes_jg.js")).use { it.readBytes() }) == expectedGlueSha) {
                    "APK glue differs from the validated core pair"
                }
                check(sha(zip.getInputStream(zip.getEntry("assets/cores/bsnes_jg.wasm")).use { it.readBytes() }) == expectedWasmSha) {
                    "APK wasm differs from the validated core pair"
                }
            }
            if (flavor == "nativeplayer") {
                check(sha(zip.getInputStream(zip.getEntry("assets/index.html")).use { it.readBytes() }) ==
                      sha(tvProject.resolve("app/src/nativeplayer/assets/index.html").readBytes())) {
                    "Standalone Native APK does not contain its direct-launch player page"
                }
                check(sha(zip.getInputStream(zip.getEntry("assets/tv-player.js")).use { it.readBytes() }) ==
                      sha(tvProject.resolve("app/src/main/assets/tv-player.js").readBytes())) {
                    "Standalone Native APK does not contain its remote-control player"
                }
            }
            if (flavor == "wasmplayer") {
                check(sha(zip.getInputStream(zip.getEntry("assets/index.html")).use { it.readBytes() }) ==
                      sha(tvProject.resolve("app/src/wasmplayer/assets/index.html").readBytes())) {
                    "Standalone WASM APK does not contain its direct-launch player page"
                }
                check(entries.contains("assets/performance-overlay.js")) {
                    "Standalone WASM APK is missing the shared performance overlay"
                }
            }
            if (flavor != "nativeplayer") {
                check(sha(zip.getInputStream(zip.getEntry("assets/roms/manifest.json")).use { it.readBytes() }) ==
                      sha(tvProject.resolve("fixture/manifest.json").readBytes())) {
                    "APK self-check metadata differs from the frozen fixture manifest"
                }
            }
            val manifestText = tvProject.resolve("app/src/main/AndroidManifest.xml").readText()
            check(manifestText.contains("android.permission.INTERNET") &&
                  manifestText.contains("android:usesCleartextTraffic=\"false\"")) {
                "APK transfer requires socket access while cleartext app traffic stays disabled"
            }
            check(tvProject.resolve("app/src/main/java/org/bsnesjg/tv/MainActivity.java")
                  .readText().contains("setBlockNetworkLoads(true)")) {
                "The WebView must remain offline while the explicit APK transfer server is available"
            }
            if (buildType == "Release") {
                val releaseManifest = zip.getInputStream(zip.getEntry("AndroidManifest.xml")).use { it.readBytes() }
                // aapt2's binary manifest marks debuggable as a typed boolean; checking
                // the generated merged manifest is more robust than searching APK bytes.
                val manifestVariant = flavor + buildType
                val mergedManifest = layout.buildDirectory.file("intermediates/merged_manifests/$manifestVariant/process${variant}Manifest/AndroidManifest.xml").get().asFile
                check(mergedManifest.isFile && !mergedManifest.readText().contains("android:debuggable=\"true\"")) {
                    "Measurement APK must be non-debuggable"
                }
                val expectedPackage = when (flavor) {
                    "wasmplayer" -> "org.bsnesjg.tv"
                    "native" -> "org.bsnesjg.tv.native.phase2"
                    "nativeplayer" -> "org.bsnesjg.tv.native"
                    else -> "org.bsnesjg.tv.phase2"
                }
                check(mergedManifest.readText().contains("package=\"$expectedPackage\"")) {
                    "$variant APK package id does not match $expectedPackage"
                }
                check(mergedManifest.readText().contains("<profileable android:shell=\"true\"")) {
                    "Measurement APK must enable shell profiling"
                }
                check(releaseManifest.isNotEmpty()) { "Release APK manifest is empty" }
            }
        }
        println("Verified $variant APK: $file (${file.length()} bytes)")
    }
}

val verifyDebugArtifact = verifyApkArtifact("verifyDebugArtifact", "WasmDebug")
val verifyReleaseArtifact = verifyApkArtifact("verifyReleaseArtifact", "WasmRelease")
val verifyWasmplayerDebugArtifact = verifyApkArtifact("verifyWasmplayerDebugArtifact", "WasmplayerDebug")
val verifyWasmplayerReleaseArtifact = verifyApkArtifact("verifyWasmplayerReleaseArtifact", "WasmplayerRelease")
val verifyNativeDebugArtifact = verifyApkArtifact("verifyNativeDebugArtifact", "NativeDebug")
val verifyNativeReleaseArtifact = verifyApkArtifact("verifyNativeReleaseArtifact", "NativeRelease")
val verifyNativeplayerReleaseArtifact = verifyApkArtifact("verifyNativeplayerReleaseArtifact", "NativeplayerRelease")
