// Library UI test: loads the real library page (android/app/src/main/assets/
// index.html, library.js, library.css, tv.js) in headless Chromium and drives
// it with keyboard events, as the Google TV remote does through the WebView.
//
// It covers verification step 1 of two plans:
//   docs/plans/2026-10-26-snes-rom-library-selector.md  (the "selector" cases)
//   docs/plans/2026-10-26-snes-rom-library-search.md    (the "search" cases)
//
// Run:  node --test android/test/library-ui.test.mjs
// Needs playwright-core and its chromium-headless-shell. See loadChromium() in
// library-ui-helpers.mjs for where it looks. Not part of build-in-container.sh:
// the build container has no Chromium.
//
// Only engine-adapter.js is replaced, by a stub with web/app.js's BJGTV shape
// that records play/resume/pause calls; BjgAndroid is a stub that records
// setPrefs and exitApp. Keys follow the plan's input model for a keyboard:
// arrows, Enter (Select) and Esc (Back).

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import {
  PUBLISHED, synthetic, singleCategory, bySlug, loadChromium, openLibrary, settle, press, state,
} from "./library-ui-helpers.mjs";

let browser;
before(async () => { browser = await (await loadChromium()).launch({ headless: true }); });
after(async () => { await browser?.close(); });

// Opens the page, runs `body`, and always closes it. Also fails the test on any
// uncaught page error, since a thrown handler would make every other assertion moot.
async function withLibrary(options, body) {
  const lib = await openLibrary(browser, options);
  try {
    await body(lib.page);
    assert.deepEqual(lib.errors, [], "the page threw");
  } finally {
    await lib.close();
  }
}

const exits = (s) => s.calls.filter((c) => c[0] === "exitApp").length;
const launches = (s) => s.calls.filter((c) => c[0] === "play" || c[0] === "resume");
const focusLucky = (page) => page.evaluate(() => document.getElementById("lucky").focus());

// Selector plan, Back ladder. The plan's status line (2026-10-29) says the later
// launcher views plan "supersedes this original Back ladder for library builds":
// Back during gameplay pauses and returns to the same selector state, with Resume
// as the primary action for the loaded ROM, and "Back from the selector exits the
// app". Verification step 1 still says "every Back-ladder rule" without saying the
// ladder changed, so the rule is ambiguous. These tests follow the plan's own
// superseding text: for each of the five original rules they check what the
// superseding rule says now happens in that situation. That text is unconditional
// ("Back from the selector exits the app"), so rules 1 to 4 all become exits.
const MANDELBROTS = ["mandel-double", "mandel-float", "mandel-oop", "mandel-display"];
const MANDEL_TITLES = ["Double-Precision Mandelbrot", "Soft-Float Mandelbrot", "Mode 7 Mandelbrot (OOP)", "Mode 7 Mandelbrot"];

// ───────────────────────────── selector plan ─────────────────────────────

test("selector: focus starts on row 1 on first launch", async () => {
  await withLibrary({ roms: synthetic(10) }, async (page) => {
    const s = await state(page);
    assert.equal(s.focusClass, "rom");
    assert.equal(s.focusIndex, "0");
    assert.equal(s.title, PUBLISHED[0].title, "the preview shows row 1");
  });
});

test("selector: focus is restored to lastPlayed on a later launch, with the filter reset to All", async () => {
  const roms = synthetic(100), last = roms[40];
  await withLibrary({ roms, prefs: { favorites: [], lastPlayed: last.slug } }, async (page) => {
    const s = await state(page);
    assert.equal(s.focusClass, "rom");
    assert.equal(s.focusIndex, "40");
    assert.equal(s.focusText.includes(last.title), true);
    assert.equal(s.activeChip, "all");
  });
});

test("selector: no Search field is shown (4 and 10 ROMs)", async () => {
  // Decision 3 removes search from this release; the search plan brings it back
  // only above 24 ROMs, so at the small counts this step uses it must be absent.
  for (const n of [4, 10]) {
    await withLibrary({ roms: synthetic(n) }, async (page) => {
      assert.equal((await state(page)).searchVisible, false, `${n} ROMs`);
    });
  }
});

test("selector: Back ladder rule 1, Back on the preview's star button (superseded: exits the app)", async () => {
  await withLibrary({ roms: synthetic(10) }, async (page) => {
    await press(page, "ArrowRight");
    assert.equal((await state(page)).focusId, "favorite", "Right from a row reaches the preview's star button");
    await press(page, "Escape");
    const s = await state(page);
    assert.equal(exits(s), 1);
    assert.deepEqual(launches(s), []);
  });
});

test("selector: Back ladder rule 2, Back while a ROM is loading (superseded: exits the app)", async () => {
  await withLibrary({ roms: synthetic(10), playMode: "pending" }, async (page) => {
    await press(page, "Enter");
    let s = await state(page);
    assert.deepEqual(s.calls, [["play", PUBLISHED[0].slug]], "Select starts the load");
    assert.equal(s.libraryVisible, true, "the load has not finished");
    await press(page, "Escape");
    s = await state(page);
    assert.equal(exits(s), 1);
  });
});

test("selector: Back ladder rule 3, Back with a game paused behind the library (superseded: exits the app)", async () => {
  await withLibrary({ roms: synthetic(10) }, async (page) => {
    await press(page, "ArrowDown", 2);
    await press(page, "Enter");
    await press(page, "Escape"); // gameplay Back: pause and return to the selector
    let s = await state(page);
    assert.equal(s.libraryVisible, true);
    assert.equal(exits(s), 0);
    await press(page, "Escape"); // Back from the selector, game still paused
    s = await state(page);
    assert.equal(exits(s), 1, "Back from the selector exits the app");
    assert.equal(s.calls.filter((c) => c[0] === "resume").length, 0, "the paused game is not resumed");
  });
});

test("selector: Back during gameplay pauses and returns to the same selector state, with Resume", async () => {
  // The superseding rule that replaces "Choose another ROM", which the pause
  // menu no longer offers.
  const roms = synthetic(100);
  await withLibrary({ roms }, async (page) => {
    await press(page, "ArrowDown", 5);
    await press(page, "Enter");
    let s = await state(page);
    assert.deepEqual(s.calls, [["play", roms[5].slug]]);
    assert.equal(s.libraryVisible, false, "the library hides once the ROM plays");
    await press(page, "Escape");
    s = await state(page);
    assert.equal(s.libraryVisible, true);
    assert.deepEqual(s.calls.at(-1), ["pause"]);
    assert.equal(s.focusIndex, "5", "focus returns to the paused ROM's row");
    assert.equal(s.activeChip, "all");
    assert.equal(s.playLabel, "▶ Resume");
    await press(page, "Enter");
    s = await state(page);
    assert.deepEqual(s.calls.at(-1), ["resume", roms[5].slug], "Select on the paused row resumes, not restarts");
  });
});

test("selector: Back ladder rule 4, Back with the list scrolled past its first screen (superseded: exits the app)", async () => {
  await withLibrary({ roms: synthetic(100) }, async (page) => {
    await press(page, "ArrowDown", 15);
    assert.equal((await state(page)).focusIndex, "15");
    await press(page, "Escape");
    assert.equal(exits(await state(page)), 1);
  });
});

test("selector: Back ladder rule 5, Back at the top with no game exits the app", async () => {
  await withLibrary({ roms: synthetic(10) }, async (page) => {
    await press(page, "Escape");
    const s = await state(page);
    assert.equal(exits(s), 1);
    assert.deepEqual(launches(s), []);
  });
});

test("selector: Hold Enter toggles a favorite without launching", async () => {
  const roms = synthetic(10);
  await withLibrary({ roms }, async (page) => {
    await press(page, "ArrowDown");
    for (const expectFavorite of [true, false]) {
      await page.keyboard.down("Enter");
      await page.waitForTimeout(700); // Hold Select is >= 500 ms
      await page.keyboard.up("Enter");
      await settle(page);
      const s = await state(page);
      assert.deepEqual(launches(s), [], "holding Enter must not launch");
      assert.equal(s.focusIndex, "1", "focus stays on the row");
      assert.equal(s.rowStars[1], expectFavorite, "the row's star");
      assert.deepEqual(s.prefWrites.at(-1).favorites, expectFavorite ? [roms[1].slug] : [], "favorites persist through setPrefs");
    }
    await press(page, "Enter"); // control: a tap does launch, so the check above can fail
    assert.deepEqual(launches(await state(page)), [["play", roms[1].slug]]);
  });
});

test("selector: I'm Feeling Lucky draws 4 distinct ROMs in 4 draws from a 4-ROM set", async () => {
  const roms = synthetic(4);
  await withLibrary({ roms }, async (page) => {
    // Lucky has no D-pad route in library.js (Up from a hidden chip row goes
    // nowhere), so the test focuses it directly and presses Select. Back returns
    // to the selector between draws, as the remote would.
    for (let round = 0; round < 5; round++) {
      const drawn = [];
      for (let i = 0; i < 4; i++) {
        await focusLucky(page);
        const before = launches(await state(page)).length;
        await press(page, "Enter");
        const s = await state(page);
        assert.equal(launches(s).length, before + 1, "each press draws one ROM");
        drawn.push(launches(s).at(-1)[1]);
        await press(page, "Escape");
      }
      assert.equal(new Set(drawn).size, 4, `round ${round + 1} drew ${drawn.join(", ")}`);
    }
  });
});

test("selector: the empty-Favorites state", async () => {
  // Mockup 02-favorites-empty: "No favorites yet" with how to add one, Lucky dimmed
  // and skipped, focus stays on the chip (nothing below it to focus).
  await withLibrary({ roms: synthetic(100) }, async (page) => {
    await press(page, "ArrowUp"); // row 1 -> active chip (All)
    await press(page, "ArrowRight"); // -> ★ Favorites
    await page.waitForTimeout(400); // a chip applies after 300 ms of rest
    await settle(page);
    const s = await state(page);
    assert.equal(s.activeChip, "favorites");
    assert.equal(s.focusText.startsWith("★ Favorites"), true, "focus stays on the Favorites chip");
    assert.equal(s.rows, 0);
    assert.equal(s.emptyVisible, true, "an empty state is shown");
    assert.equal(s.luckyDisabled, true, "I'm Feeling Lucky is dimmed with no results");
    assert.match(s.emptyText, /No favorites yet/, "the empty state says there are no favorites yet (mockup 02)");
  });
});

test("selector: layout at 1 ROM boots the ROM directly", async () => {
  const roms = synthetic(1);
  await withLibrary({ roms }, async (page) => {
    const s = await state(page);
    assert.deepEqual(s.calls, [["play", roms[0].slug]]);
    assert.equal(s.libraryVisible, false);
    assert.equal(s.playing, true);
  });
});

test("selector: layout at 10 ROMs is list and preview, no filter chips, Lucky shown", async () => {
  await withLibrary({ roms: synthetic(10) }, async (page) => {
    const s = await state(page);
    assert.equal(s.libraryVisible, true);
    assert.equal(s.listVisible, true);
    assert.equal(s.previewVisible, true);
    assert.equal(s.rows, 10);
    assert.equal(s.filtersVisible, false, "2-12 ROMs: chips hidden");
    assert.equal(s.luckyVisible, true);
  });
});

test("selector: layout at 13+ ROMs in one category hides the filter chips", async () => {
  // Catalog-size table: 13+ is the full layout with chips "Shown if there are >= 2 categories".
  await withLibrary({ roms: singleCategory(13) }, async (page) => {
    const s = await state(page);
    assert.equal(s.filtersVisible, false, "one category: no chips");
    assert.equal(s.luckyVisible, true);
  });
});

test("selector: layout at 100 ROMs is the full layout with chips and Lucky", async () => {
  await withLibrary({ roms: synthetic(100) }, async (page) => {
    const s = await state(page);
    assert.equal(s.listVisible, true);
    assert.equal(s.previewVisible, true);
    assert.equal(s.filtersVisible, true);
    assert.equal(s.chipCount >= 4, true, "All, Favorites and at least 2 categories");
    assert.equal(s.luckyVisible, true);
  });
});

test("selector: layout at 1,000 ROMs is the full layout with chips and Lucky", async () => {
  await withLibrary({ roms: synthetic(1000) }, async (page) => {
    const s = await state(page);
    assert.equal(s.listVisible, true);
    assert.equal(s.previewVisible, true);
    assert.equal(s.filtersVisible, true);
    assert.equal(s.luckyVisible, true);
  });
});

test("selector: at most 30 rows in the DOM with 1,000 ROMs", async () => {
  const roms = synthetic(1000);
  await withLibrary({ roms }, async (page) => {
    assert.ok((await state(page)).rows <= 30, "at the top");
    await press(page, "ArrowDown", 40);
    const s = await state(page);
    assert.equal(s.focusIndex, "40");
    assert.ok(s.rows <= 30, `after 40 rows down: ${s.rows}`);
  });
  await withLibrary({ roms, prefs: { lastPlayed: roms[999].slug } }, async (page) => {
    const s = await state(page);
    assert.equal(s.focusIndex, "999");
    assert.ok(s.rows <= 30, `restored to the last row: ${s.rows}`);
  });
});

// ────────────────────────────── search plan ──────────────────────────────
// These use the full 152-ROM published catalog, so the field is shown.

async function typeSearch(page, text) {
  // The plan has Select on the field open the system keyboard; the page cannot
  // see that keyboard, so the test focuses the field and types into it.
  await page.focus("#search");
  await page.keyboard.type(text);
  await page.waitForTimeout(150); // results are debounced by up to 100 ms
  await settle(page);
}

test("search: `mand` returns 4 results with TOP MATCH on the first", async () => {
  await withLibrary({ roms: synthetic(152) }, async (page) => {
    await typeSearch(page, "mand");
    const s = await state(page);
    assert.deepEqual(s.rowTitles, MANDEL_TITLES, "all four, ties in gallery order");
    assert.equal(s.rowTags[0].includes("TOP MATCH"), true);
    assert.deepEqual(s.rowTags.slice(1).map((t) => t.includes("TOP MATCH")), [false, false, false]);
  });
});

test("search: `gf28` finds GF(2⁸) and `pi` finds the π Spigot", async () => {
  await withLibrary({ roms: synthetic(152) }, async (page) => {
    await typeSearch(page, "gf28");
    assert.deepEqual((await state(page)).rowTitles, ["GF(2⁸) Galois Field"]);
    await page.fill("#search", "");
    await typeSearch(page, "pi");
    assert.equal((await state(page)).rowTitles.includes("π Spigot + Monte-Carlo"), true);
  });
});

test("search: Enter in the field focuses the TOP MATCH row without launching it", async () => {
  await withLibrary({ roms: synthetic(152) }, async (page) => {
    await typeSearch(page, "mand");
    await press(page, "Enter");
    await page.waitForTimeout(700); // longer than Hold Select, in case Enter's keyup reached the row
    const s = await state(page);
    assert.equal(s.focusClass, "rom");
    assert.equal(s.focusIndex, "0");
    assert.equal(s.focusText.includes("TOP MATCH"), true);
    assert.deepEqual(launches(s), []);
    await press(page, "Enter"); // control: Select then plays it
    assert.deepEqual(launches(await state(page)), [["play", "mandel-double"]]);
  });
});

test("search: an empty result inside a filter offers Search all N ROMs with the right count", async () => {
  // Plan: the empty result "offers Search all N ROMs, which takes focus and
  // already shows the global match count". Mockup 02-no-matches reads "1 match in
  // all ROMs." above "Search all 152 ROMs": N is the catalog size, and the global
  // match count is shown with it. "Takes focus" is checked after the keyboard's
  // action key (Enter), since focus must not leave the field while typing.
  const roms = synthetic(152);
  await withLibrary({ roms }, async (page) => {
    await press(page, "ArrowUp"); // row 1 -> All chip
    const steps = await page.evaluate(() => Array.from(document.querySelectorAll("#filters .chip")).findIndex((c) => c.dataset.key === "fractals"));
    await press(page, "ArrowRight", steps);
    await page.waitForTimeout(400);
    assert.equal((await state(page)).activeChip, "fractals");
    await typeSearch(page, "gf28"); // GF(2⁸) is in Ciphers & Bit Tricks
    await press(page, "Enter");
    const s = await state(page);
    assert.equal(s.rows, 0);
    assert.equal(s.emptyVisible, true);
    assert.equal(s.searchAllVisible, true);
    assert.equal(s.focusId, "search-all", "Search all takes focus");
    // Both checked at once so a failure reports each of them.
    assert.deepEqual(
      { globalCountShown: /\b1 match\b/.test(s.emptyText), searchAllLabel: s.searchAllText },
      { globalCountShown: true, searchAllLabel: `Search all ${roms.length} ROMs` });
  });
});

test("search: I'm Feeling Lucky draws only from the search results", async () => {
  await withLibrary({ roms: synthetic(152) }, async (page) => {
    await typeSearch(page, "mand");
    const drawn = [];
    for (let i = 0; i < 8; i++) {
      await focusLucky(page);
      await press(page, "Enter");
      drawn.push(launches(await state(page)).at(-1)[1]);
      await press(page, "Escape"); // back to the selector; the search text is kept
    }
    assert.deepEqual(drawn.filter((slug) => !MANDELBROTS.includes(slug)), [], `drew ${drawn.join(", ")}`);
    assert.equal(new Set(drawn.slice(0, 4)).size, 4, "the shuffle bag covers all four before repeating");
  });
});

test("search: the field is hidden at 24 ROMs and shown at 25", async () => {
  await withLibrary({ roms: synthetic(24) }, async (page) => {
    assert.equal((await state(page)).searchVisible, false, "24 ROMs");
  });
  await withLibrary({ roms: synthetic(25) }, async (page) => {
    assert.equal((await state(page)).searchVisible, true, "25 ROMs");
  });
});
