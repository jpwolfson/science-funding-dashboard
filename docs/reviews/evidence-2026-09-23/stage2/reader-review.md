# Reader review: federal science funding site (rendered screenshots)

## Reviewer context

- **Build context: none.** I did not read any repository, source code, documentation, commit history or earlier review. I ran no commands except the ones needed to crop and view images.
- **Input:** only the 74 full-page PNG screenshots (1100 px wide, light mode) in `scratchpad/reader-pack/`. I cropped them into 1100 px strips with a 60 px overlap (in `scratchpad/reader-strips/`). Where text was small I made zoom crops, side-by-side composites and bottom-of-page composites.
- **Stance:** I read each page as a first-time visitor would, such as a policy staffer or journalist. Every number and quotation below comes from the rendered pages. Where I say a reading is likely false, I base it on what the pages themselves show, such as a contradiction between two pages, a disclosed scope or a missing note. I did not use outside data.

### Files reviewed in full (25)

Award tab (6): `award-root.png`, `award-nih.png`, `award-nih-cc.png`, `award-nsf.png`, `award-nsf-bfa.png`, `award-nsf-bfa-bfa.png`

Obligations landing and sentinel (2): `obligations-landing.png`, `sentinel.png`

Obligation accounts (12): `obligations-account-dod-navy-rdte.png`, `obligations-account-dod-defense-wide-rdte.png`, `obligations-account-dod-defense-health-program.png`, `obligations-account-doe-sc.png`, `obligations-account-commerce-nist-its.png`, `obligations-account-commerce-noaa-orf.png`, `obligations-account-dhs-cisa-rd.png`, `obligations-account-nsf-rra.png` (NSF), `obligations-account-nasa-science.png` (NASA), `obligations-account-usda-nifa-research-education.png` (USDA), `obligations-account-epa-science-technology.png` (EPA), `obligations-account-va-medical-prosthetic-research.png`

Program-activity pages (5): `obligations-pa-dod-basic-research.png`, `obligations-pa-doe-basic-energy-sciences.png`, `obligations-pa-nasa-science-direct.png`, `obligations-pa-nsf-unknown-other.png`, `obligations-pa-hhs-administration-for-strategic-preparedness-and-response.png`

### Files skimmed for anything unlike their siblings (49)

I skimmed these using header crops, half-scale composites of the middle of each page and a composite of each page's "File C / net" footer line. For the Army and Air Force pages I also read the charts at full size.

Accounts (41): `commerce-census-current-surveys`, `commerce-census-periodic-censuses`, `commerce-nist-strs`, `commerce-noaa-pac`, `dhs-cwmd-rd`, `dhs-science-technology-rd`, `dod-air-force-rdte` (charts read in full), `dod-army-rdte` (charts read in full), `dod-space-force-rdte`, `doe-arpa-e`, `doe-ceser`, `doe-eere`, `doe-eia`, `doe-electricity`, `doe-fossil-energy`, `doe-nnsa-defense-nuclear-nonproliferation`, `doe-nnsa-weapons-activities`, `doe-nuclear-energy`, `doe-oced`, `doi-usgs-sir`, `dot-faa-research-engineering-development`, `dot-fra-rd`, `dot-ost-research-technology`, `ed-ies`, `hhs-ahrq`, `hhs-aspr-rd-procurement`, `nasa-aeronautics`, `nasa-exploration`, `nasa-space-operations`, `nasa-space-technology`, `nasa-stem-engagement`, `nsf-aoam`, `nsf-mrefc`, `nsf-stem-education`, `usda-ars-buildings-facilities`, `usda-ars-salaries-expenses`, `usda-ers`, `usda-forest-rangeland-research`, `usda-nass`, `usda-nifa-extension`, `usda-nifa-integrated-activities`. Every file name has the `obligations-account-` prefix and a `.png` suffix.

Program-activity "Unknown / other" pages (8): `obligations-pa-commerce-unknown-other`, `-dhs-`, `-doi-`, `-dot-`, `-ed-`, `-epa-`, `-usda-`, `-va-unknown-other` (`.png`)

---

## Ranked cross-page findings

"Fix" is a one-line suggestion for correcting the reading. It is not a code proposal.

| # | Severity | Finding | Page(s) | Exact evidence |
|---|---|---|---|---|
| 1 | **High** | The obligation ledger is headlined as federal **science**, but its totals include large non-research lines: military health care operations, nuclear-weapons activities, drug stockpile procurement and DoD prototyping. A first-time reader will take "$285.826B" as the size of federal science obligations and conclude that DoD is 72% of federal science. *Fix: show a research-only subtotal, or retitle to "science-related accounts (incl. defense RDT&E, NNSA, military health)" and show each account's R&D share.* | obligations-landing; dod-defense-health-program; doe-nnsa-weapons-activities (skim); obligations-pa-hhs-aspr | Landing H1 "Federal science obligation dashboard". Cards "Net obligations, FY2026 to date $285.826B"; "$2703.529B net obligations across 502,002 distinct linked awards, FY2017–FY2026 combined"; "DOD — Department of Defense * $206.076B". DHP program-activity row "Operation and Maintenance $37.974B" out of a $41.069B account. Weapons Activities FY26 $27.388B. The landing top-recipient list is TRIAD NATIONAL SECURITY $5.143B, NTESS (Sandia) $4.665B, LLNS $3.370B, CONSOLIDATED NUCLEAR SECURITY $3.072B … PANTEXAS DETERRENCE $1.606B. ASPR negative flow "AMOXICILLIN TRIHYDRATE 500 MG ORAL CAPSULES 60 AND 100 COUNT BOTTLES −$42.2M". The DHP top recipients include "AWS CLOUD SERVICES-COMMERCIAL" and "PATIENT APPOINTING SERVICES". |
| 2 | **High** | NIH is missing from the obligation ledger, and the landing page never says so. The HHS row reads as all of HHS science obligations, and it conflicts by an order of magnitude with the NIH figures on the award tab. *Fix: add an "NIH obligation accounts not included" line to the HHS row and the landing intro.* | obligations-landing; award-root; award-nih | Landing: "HHS — Department of Health and Human Services $2.333B 70.8% 220". Award tab: "NIH — National Institutes of Health 40,275 … $24.407B". The landing intro says only "Obligations from 53 registered science-related federal accounts, including defense RDT&E." |
| 3 | **High** | Program-activity rows that appear to be retired or renamed codes are shown with "Net obligations FY2026 to date $0". Named research programs therefore read as eliminated in FY2026. *Fix: label them "inactive code (last used FYxxxx)" or fold them into a collapsed "historical codes" row.* | epa-science-technology; dod-defense-health-program; usda-nifa-research-education; va-medical-prosthetic-research; commerce-nist-its; commerce-noaa-orf | EPA: "RESEARCH: AIR, CLIMATE AND ENERGY $0 — 0", "RESEARCH: CHEMICAL SAFETY AND SUSTAINABILITY $0 — 0", "RESEARCH: SAFE AND SUSTAINABLE WATER RESOURCES $0 — 0", "HUMAN HEALTH RISK ASSESSMENT $0 — 0", "INDOOR AIR: RADON PROGRAM $0". About 70 such rows sit beside new goal-style rows such as "CROSS-AGENCY MISSION AND SCIENCE SUPPORT $362M". DHP: "BASIC RESEARCH $0 — 0", "APPLIED RESEARCH $0 — 0", "USUHS $0". NIST: "Technology Innovation Program $0". VA: "MILLION VETERANS PROGRAM $0" directly under "MILLION VETERANS PROGRAM (826) $77.6M". Some $0 rows still carry awards: NIFA "ALFALFA FORAGE AND RESEARCH PROGRAM $0 — 3". |
| 4 | **High** | Army RDT&E has a doubled FY21–FY22, a cumulative line that climbs to about $82B and then falls, and a single −$32B reporting period. None of this has a "Notes on source figures" box, even though smaller anomalies on NIST ITS and CISA get one. A reader will conclude that Army R&D was halved after FY2022, or that $32B was clawed back in 2022. *Fix: add a source-figures note, or flag FY21–22 as source-anomalous.* | dod-army-rdte (charts read in full); obligations-landing (inherits) | FY bars: '20 about $29B, **'21 about $56B, '22 about $52.5B**, '23 $28.3B, '24 $24.6B, '25 $24.3B. Cumulative "FY22 · $52.527B" after rising to about $82B by Jul. The period chart has a first step of about +$42B at 2022P07 and a step of about **−$32B**, with the y-axis running to "−$60B". No notes box appears between the FY chart and "Top recipients". |
| 5 | **High** (sentinel language) | Both source-confirmed termination cards lead with **"$0 gross negative · $0 net"**, and the NSF card contradicts itself. A reader will conclude either that the terminations had no financial effect or that the numbers are broken. *Fix: replace "$0" with "not joined to obligation ledger", and rename the count "award IDs listed by source".* | sentinel | "DOE portfolio-action announcement — October 2025 **$0 gross negative · $0 net** [Source-confirmed event]", directly above "Attributed source headline: 'Energy Department Announces Termination of 223 Projects, Saving Over $7.5 Billion'". "NSF termination list — June 2025 $0 gross negative · $0 net" followed by "**$0 gross negative activity  $0 net activity  1,667 award IDs with negative entries**". |
| 6 | **High** (sentinel language) | The sentinel's "net" is a different measure from the ledger's "net", and the two pages give opposite signs for the same office. The NOAA episodes add up to about −$1.7B and read as NOAA losing that much in FY2026. The NOAA ORF page shows FY26 net obligations of +$3.651B, and its largest single negative award flow is −$9.2M. *Fix: rename the measure "net File C in flagged periods" and show the program activity's FY net obligation beside it.* | sentinel; commerce-noaa-orf; nasa-science / pa-nasa-science-direct | Sentinel: "National Marine Fisheries Service · NOAA ORF · FY2026 **−$526M gross negative · −$520M net** … 1,769 award IDs". ORF program-activity table: "NMFS — National Marine Fisheries Service **$520M** −52.2% 1,934". Other sentinel NOAA ORF episodes: NOS "−$470M net", OAR "−$337M net", NWS "−$228M net", NESDIS "−$83.4M net", ARPA-C "−$39.7M net". ORF page: "Net obligations, FY2026 to date $3.651B", "File C portion … −$655M". Its largest negative flow is "−$9.2M" (USVI DPNR). NASA sentinel card: "−$26.1M gross negative". NASA page: "Negative ledger entries … −$93.8M". The difference is not explained. |
| 7 | **High** (public-claim risk) | On the USDA NIFA page, the award-title column for red "Negative entry" rows shows an agency political disclaimer. Together they imply that prior-administration awards were terminated for political reasons, a motive the site itself says it cannot infer. *Fix: show the substantive award title, or mark boilerplate as "agency-supplied text" and keep it apart from the amount.* | usda-nifa-research-education | Utah State: "** AWARDS ISSUED PRIOR TO JANUARY 20, 2025, WERE FUNDED UNDER PREVIOUS ADMINISTRATIONS AND MAY NOT REFLECT THE PRIORITIES AND POLICIES OF T…" "Negative entry −$1.5M". The same text appears on NC State −$721K, North Dakota State −$676K and Virginia Tech −$644K. The sentinel says separately: "No motive inference." |
| 8 | Med | The award tab has an unannotated two-month near-zero cliff (Oct–Nov 2025) inside the Oct–Jul comparison window that drives every headline percentage. FY26 cumulative lines stay flat until December. A reader cannot tell whether this is a funding collapse, a pause or missing data. *Fix: annotate the gap and give its cause, or add a Dec–Jul comparison.* | award-root; award-nih; award-nsf | The monthly charts drop to about 150 in two consecutive months in late 2025. The cards read "−18.3% vs FY15–24 avg" (root), "−13.1%" (NIH) and "**−46.3%**" (NSF new awards), plus "Continuing grants … −69.1%". The "FY2026 (to date)" cumulative line is at about 0 for Oct–Nov. |
| 9 | Med | The root page is titled "Federal science funding dashboard", but its headline cards cover only NIH and NSF. "−18.3%" reads as all federal science. *Fix: put "NIH + NSF" in the card labels or the H1.* | award-root | "Awards, FY2026 Oct–Jul 44,845 −18.3% vs FY15–24 avg". The scope appears only in body text: "Award ledger: NIH and NSF, 87 units." |
| 10 | Med | Red "−100.0%" on NSF administrative offices reads as a FY2026 elimination. The last awards were in FY2022, and they were interagency admin agreements counted as "science awards". *Fix: suppress % change when the baseline is tiny or the unit is inactive, and mark non-research offices.* | award-nsf; award-nsf-bfa; award-nsf-bfa-bfa | NSF directorates table: "BFA — Office of Budget, Finance, & Award Management 0 **−100.0%** $0K 76", "IRM … 0 −100.0% $0K 148". BFA cards: "New awards 0 −100.0%", "Intended $ $0.0M −100.0%". Its "largest awards" are "IAE Loans and Grants" (GSA, $720K), "FY 22 Grants.gov" (HHS, $326K) and "FY22 Indirect Cost Negotiation IAA" (Bureau of Reclamation, $307K). |
| 11 | Med | NIH units with zero awards ever appear as linked rows and as a full "funding dashboard" of zeros, with no explanation. A reader will conclude that the NIH Clinical Center receives no funding. *Fix: add a one-line "intramural / not an extramural grant-maker" note, or hide the rows.* | award-nih; award-nih-cc | Rows "CC — NIH Clinical Center 0 — $0K 0", "CSR — Center for Scientific Review 0 — $0K 0" and "CIT — Center for Information Technology 0 — $0K 0". The CC page title is "NIH Clinical Center — funding dashboard" with "$0.0M", "baseline n/a", four empty charts and "$0M" repeated on the y-axis. |
| 12 | Med | NIST ITS: the FY25 cumulative line jumps to about $5.7B and then collapses. The note names the $5.03B deobligation but not the program or award, or whether it was a restructuring or a cancellation. The partial-year FY26 bar is the tallest. Readers will infer a $5B CHIPS clawback followed by a FY26 surge. *Fix: name the program activity and link the source.* | commerce-nist-its | "FY2025, period 11: … the source reports a net deobligation of $5.03 billion, taking cumulative net obligations for the year from $5.73 billion after period 10 to $0.70 billion." Rows "CHIPS $900M −0.0% 3" and "FY26 · $1.011B"; the '26* bar is above '25 ($719M). |
| 13 | Med | Air Force RDT&E: missing FY24 periods create a plateau followed by a $32B single-period spike. On the period charts, including the landing's roll-up, this reads as an August 2024 surge. *Fix: annotate catch-up periods on the period chart as well as on the cumulative one.* | dod-air-force-rdte; obligations-landing | The FY24 cumulative line is flat at about $14B, with hollow points from Feb to Aug, and then jumps to "FY24 · $50.929B". The period chart shows about $32B at "2024P11". The landing period chart shows about $85B around 2024P11. |
| 14 | Med | Landing FY bars mark alternating "partial" years in the middle of the series. The rise from about $187B to $345B mixes coverage changes with real growth, and the page never says what is missing. *Fix: state the share of accounts with full history for each FY.* | obligations-landing; obligations-pa-hhs-aspr | Bars '17*, '19*, '22*, '24*, '26* with the footnote "* partial fiscal year (source history or year in progress)". Legend entries "FY2024 (partial source history)" and "FY2022 (partial source history)" (FY2023 has none). The ASPR series starts at "2024P06". |
| 15 | Med | Signed "File C / net" ratios produce numbers that read as data errors and erode trust. *Fix: show "n/m" when net is near zero or the signs differ.* | pa-nsf-unknown-other; pa-ed/dhs-unknown-other; doe-oced; commerce-noaa-pac; doe-fossil-energy; usda-nifa-*; dod-navy-rdte; pa-dod-basic-research | "File C / net is **100167255.7%**" (NSF Unknown/other), "10204.0%" (ED), "3298.9%" (DHS), OCED card "(**−3881.2% of net**) −$609M", NOAA PAC NOS "−1513.3%", FE "Unconventional FE Technologies $1K −28409.5%", NIFA "SET ASIDE 1500 $11K −4867.5%", Navy "Undistributed $4.4M −653.2%". DoD Basic Research reports "File C / net is 215.1%" for its full history but "0.0%" and "0" awards for FY26. |
| 16 | Med | "Unknown / other" pages combine large dollar or award figures with empty charts. A reader will see either unaccounted money or broken data. *Fix: explain the bucket (pre-FY2018 or unmapped codes), and hide pages that are entirely zero.* | pa-nsf-unknown-other; pa-va/doi/dot/epa/commerce-unknown-other | "**$25K net obligations across 72,755 distinct linked awards**" (NSF, with y-axes labelled "$0K" five times); "$655M net obligations across 0 distinct linked awards" (VA); "$0 net obligations across 0 distinct linked awards" (DOI, DOT); EPA's FY25 cumulative line ends at about −$201M; NOAA's FY22 and FY23 lines run negative (about −$311M and −$257M). |
| 17 | Med | Sentinel source freshness shows "current" for snapshots that are 12–15 months old, with raw machine timestamps. A reader assumes the lists are up to date. *Fix: show "source last changed" and "last checked" as dates.* | sentinel | "DOE October 2025 portfolio-action announcement \| current \| 2025-10-01"; "NSF terminated awards list \| current \| 2025-06-05 \| 1,667"; "2026-09-22T16:56:23.377403+00:00". |
| 18 | Med | Surges and cliffs driven by supplemental or one-time funding are not annotated, so the FY26 drops read as cuts. *Fix: tag supplemental (IIJA/IRA/CHIPS/decennial) program activities or years.* | doe-eere; doe-electricity; doe-oced; commerce-census-periodic-censuses; nsf-stem-education (all skim) | EERE FY25 $17.130B against $2–8B in other years, and FY26 $1.643B. Electricity FY24 $4.702B and FY25 $5.358B against about $0.2B in FY17–22, and FY26 $210M. OCED FY25 $8.441B against "Net obligations, FY2026 to date $15.7M". Census FY20 bar about $6.6B. |
| 19 | Low | Sentinel counting and relevance. One program is split into three "episodes", and a positive-net nuclear-weapons line is counted as an unreviewed signal. Both inflate "Unreviewed signals 174". | sentinel | "Advanced Industrial Facilities Deployment Program · OCED · FY2026" appears three times (−$95.0M, −$74.9M, −$51.0M). "Weapons Activities (Direct) · NNSA WA · FY2026 −$1.004B gross negative · **$1.981B net** … State: net activity in this period was positive." Also "1 award IDs". |
| 20 | Low | Duplicate recipients in top-10 lists make the rankings look wrong. | nasa-science; pa-nasa-science-direct; dod-defense-wide-rdte | "1 CALIFORNIA INSTITUTE OF TECHNOLOGY $1.419B" and "9 CALIFORNIA INSTITUTE OF TECHNOLOGY $65.9M". "1 LOCKHEED MARTIN CORPORATION $275M" and "6 LOCKHEED MARTIN CORPORATION $27.4M". |
| 21 | Low | Raw system codes and escaping artifacts appear as award titles. | landing; doe-sc; pa-doe-bes; pa-hhs-aspr; dod-navy-rdte; usda-nifa-r&e; epa | "IGF::CL::IGF COMPETITION FOR MANAGEMENT AND OPERATION OF LOS ALAMOS…", "TAS::89 0222::TAS MANAGEMENT AND OPERATION OF THE THOMAS JEFFERSON…", "IGF::OT::IGF", "NCA<(>&<)>T", "DESCRIPTION:THIS APPLICATION PROPOSES…". |
| 22 | Low | Internal inconsistencies on the award tab. The mechanism components don't sum to the headline card. The cards (Oct–Jul) and the cumulative endpoints (September) give two different FY26 totals. A data-quality note is duplicated. Labels are clipped. | award-root; award-nih; award-nsf | 13,212 + 28,776 + 2,460 = 44,448, against "44,845". NSF 3,756 + 615 + 54 = 4,425, against "4,570". Card "$27.948B" against "FY26 · $40.977B". "NSF: 7 awards appear in more than one division…" followed by "7 awards appear in more than one division…". Labels "28776 continuin", "13212 new/stan", "9456 new/comp". A chart subtitled "Full fiscal years" includes '26*. |
| 23 | Low | The BFA pages are broken in several ways: stale "last three fiscal years", missing FY lines, a collision with the hairline label, identical parent and leaf titles, and a raw API URL as the subtitle. | award-nsf-bfa; award-nsf-bfa-bfa | "Largest awards, last three fiscal years" lists FY2022, FY2021 and FY2020. The cumulative charts have only "FY2022". The hairline label is obscured by a bar ("F█-24 avg 4"). Both pages carry the H1 "Office of Budget, Finance, & Award Management — funding dashboard". The subtitle is "https://api.nsf.gov/services/v1/awards.json?org_code_div=10000000 …". |
| 24 | Low | CISA R&D's FY25 bar is at about $0, a visual collapse. The note is good but hedged, and its label, "FY2025, period 12", describes year totals. | dhs-cisa-rd | "The source reports $3.31 million for this account in FY2024 and $98 in FY2025. Source figures alone do not show whether the activity ended or moved to another account." |
| 25 | Low | VA and other 0%-File-C accounts lack an interpretation note equivalent to DoD's, so "0 distinct linked awards" reads as a hiding or reporting failure. | va-medical-prosthetic-research; commerce-census-current-surveys | "$8.782B net obligations across 0 distinct linked awards". "File C / net is 0.0%". Census current surveys shows 0.1%. |
| 26 | Low | Generic or duplicate page titles, and one duplicate page. | nasa-science and pa-nasa-science-direct; epa; pa-dod-basic-research; pa-*-unknown-other | "Science — obligation dashboard" is identical, number for number, to "Science (Direct) — obligation dashboard". Other titles: "Science and Technology — obligation dashboard" (EPA); "Basic Research — obligation dashboard" (Army; says Army only in the breadcrumb); "Unknown / other — obligation dashboard". |
| 27 | Low | Chart rendering anomalies. | commerce-noaa-orf; pa-nsf-unknown-other; many flow tables | NOAA ORF cumulative chart shows the label "FY24 · $7.250B" but no FY24 line, and the period axis jumps from "2023P09" to "2024P12". NSF Unknown/other shows a third end-label clipped under "FY25 · $0". In several flow tables the minus sign wraps onto its own line ("−" / "$42.3M"). |
| 28 | Low | Internal process text appears on a public page. | sentinel | "Estimated pilot burden … These are planning ranges. Replace them with measured figures after eight weeks without delaying publication, account fan-out, or closing this implementation phase." |

---

## Per-page answers (pages read in full)

### award-root: "Federal science funding dashboard"

**(a) First-time conclusion.** Federal science awards are down sharply: 44,845 awards in Oct–Jul, "−18.3% vs FY15–24 avg". Award dollars are about flat ("$27.948B −0.9%"). New awards are down 27.1%. NSF is hit much harder ("−46.3%") than NIH ("−13.1%"). FY2026 started very late, with almost nothing in Oct–Nov.

**(b) Most misleading reading.** "The federal government cut science awards by nearly a fifth." The cards cover only NIH and NSF. The scope appears only in the body text "Award ledger: NIH and NSF, 87 units." The comparison window includes two near-zero months that the page never explains.

**(c) Implies more than the data supports.**
- H1 "Federal science funding dashboard" combined with the unqualified cards "Awards, FY2026 Oct–Jul".
- The "Award dollars by fiscal year" subtitle "Full fiscal years…" sits over a pale "'26*" bar. The pale styling signals a partial year, but the subtitle contradicts it.
- "Cumulative awards through the fiscal year" invites comparing the endpoints "FY26 · 63,178" and "FY25 · 69,311" even though FY26 ends in mid-September.

**(d) Anomalies.**
- The "Awards per month" line falls to about 150 in two consecutive months in late 2025, a cliff with no annotation. The FY26 cumulative lines are flat until December.
- The card components don't reconcile: 13,212 new/standard + 28,776 continuing + 2,460 fellowships = 44,448, against 44,845.
- A data-quality note is duplicated: "NSF: 7 awards appear in more than one division…" and "7 awards appear in more than one division…". The second has no agency prefix.
- Mechanism end-labels are clipped ("28776 continuin", "13212 new/stan"), and the y-axis labels on the FY and mechanism charts are left-clipped.
- The footer date "last updated September 23, 2026" differs from the obligations tab (September 22).
- The orphan line "counts as of the pull date; NIH revises award notice dates and amounts." sits detached under the metadata line.

### award-nih: "National Institutes of Health — funding dashboard"

**(a)** NIH awards are down 13.1% in count while dollars are up 1.9%. New/competing awards are down 20.8%. Most institutes are down, and a few are up (NIA +5.8%, OD +20.0%, FIC +26.2%). Nursing (−38.6%) and Complementary Health (−32.3%) are down most.

**(b)** "NIH is funding far fewer projects." The count fall is partly the unexplained Oct–Nov 2025 gap. Dollars are up, and the page does say mechanism shifts can move counts ("Interpret the mechanism chart before reading a headline count change as a funding cut").

**(c)** The red/green % column for each institute invites ranking which institutes were "cut", with no confidence caveat for small units (NLM "107 −21.7%"). Three linked rows show "0 — $0K 0" (CC, CSR, CIT), which reads as defunded.

**(d)**
- Oct–Nov 2025 near-zero cliff in "Award records per month", unannotated.
- "FY26 · 56,412" cumulative against the Oct–Jul card "40,275": two FY26 totals on one page.
- Mechanism labels clipped ("9456 new/comp", "28161 noncomp").
- The FY15–24 average hairline label reads "FY15–24 avg 46357", unformatted, while the rest of the page uses thousands separators.

### award-nih-cc: "NIH Clinical Center — funding dashboard"

**(a)** The NIH Clinical Center gets no funding: "0 awards since Oct 2014", "$0.0M".

**(b)** That the Clinical Center, the flagship NIH research hospital, receives no federal funding, or has been defunded.

**(c)** "funding dashboard" in the H1 together with "$0.0M". Nothing says that this unit is intramural and has no extramural awards in this source. "Pagination verified … this institute's award-level dataset is stored as compressed fiscal-year CSV shards" implies there is a dataset to look at.

**(d)**
- Every chart is empty. The y-axis runs 0–1 in 0.25 steps, and the dollars chart has "$0M" five times.
- "* fiscal year in progress" appears with no starred bar.
- The cards show "baseline n/a" with no explanation.

### award-nsf: "U.S. National Science Foundation — funding dashboard"

**(a)** NSF is in steep decline: new awards "4,570 −46.3%", intended dollars "−16.6%", continuing grants "−69.1%". SBE is down 85.2% and EDU 70.3%. The FY26 cumulative line is far below every prior year and flattens in September.

**(b)** "NSF funding has been cut in half." Counts fell far more than dollars (−46.3% against −16.6%). The continuing-grant collapse from about 1,950 in FY24 to 615 may partly reflect a mechanism change, which the page itself warns about. The Oct–Nov cliff is unexplained.

**(c)** The directorates table puts administrative offices among the science directorates with red "−100.0%": "BFA … 0 −100.0%" and "IRM … 0 −100.0%". This implies they were eliminated in FY2026, but they have had no awards since about FY2022.

**(d)**
- The Oct–Nov 2025 near-zero cliff.
- The label "107 · Sep 2026 to date" overlaps the line.
- Card components don't sum: 3,756 + 615 + 54 = 4,425, against 4,570.
- The data-quality note "7 awards appear in more than one division; counted once in this rollup" gives no directorate.
- Rows for NCO, NNCO and OCIO carry 2–4 awards ever.

### award-nsf-bfa: "Office of Budget, Finance, & Award Management — funding dashboard"

**(a)** This office's awards dropped to zero this year ("−100.0%").

**(b)** That NSF eliminated a funding office in FY2026, or that the office was a science funder. Its "awards" are interagency agreements for grants.gov, the GSA award-management system and indirect-cost negotiation.

**(c)** Red "−100.0% vs FY15–24 avg" on three cards against a baseline of about 5 awards a year. Calling these "science funding" and "Largest awards" overstates them.

**(d)**
- "Largest awards, last three fiscal years" shows FY2022/2021/2020, not the last three years.
- The cumulative charts show only an FY2022 line, with no FY2026 "to date" line.
- The Oct–Jul bar chart's x-axis stops at '22, and the hairline label collides with a bar.
- The dollars chart has no '26*, but the footnote "* fiscal year in progress" is present.
- The division table shows "—" for "vs FY15–24 avg" on every row, while the parent card shows −100.0%.

### award-nsf-bfa-bfa (leaf)

**(a) and (b)** Same as the parent page.

**(c)** The subtitle is a raw API URL ("https://api.nsf.gov/services/v1/awards.json?org_code_div=10000000 (NSF Award Search API)…"), which a policy reader will not parse. Parent and leaf have the same H1, and only the breadcrumb "BFA › BFA" separates them.

**(d)**
- "FY22 · 12" here against "FY22 · 13" on the parent. That is consistent (siblings add one), but the page doesn't say so.
- The hairline label is obscured ("F█-24 avg 4").
- The same stale FY2020–22 "last three fiscal years" list appears.

### obligations-landing: "Federal science obligation dashboard"

**(a)** Federal science obligations total $285.8B in FY2026 through July, "$2703.529B" across FY2017–26. DoD is by far the largest ($206B). FY26 is running at or above prior years. Obligations have grown steadily from about $187B (FY17) to $345B (FY25). The biggest science recipients are the national-lab contractors (Triad/Los Alamos, Sandia, Livermore, Y-12/Pantex).

**(b)** "The US spends about $286B a year on science, three-quarters of it at DoD, and HHS spends only $2.3B." Both halves are distorted:
- The ledger includes military health-care operations (DHP O&M $37.974B), nuclear-weapons activities and stockpile procurement.
- It excludes NIH without saying so on this page.

**(c)**
- "science-related federal accounts, including defense RDT&E" understates what is included: health care O&M, weapons activities and procurement.
- A top-10 recipient list made up entirely of nuclear-weapons M&O contractors (and Pantexas Deterrence) under "Top recipients of award-attributed obligations" implies these are science recipients.
- The FY bar chart alternates partial ("'19*", "'22*", "'24*") and full years, so the rising trend partly reflects coverage.
- "DOD — Department of Defense *" does carry an appropriate footnote.

**(d)**
- The period chart peaks at about $85B around 2024P11. This is the Air Force catch-up, and it is unannotated.
- The FY2022 and FY2024 legend entries say "(partial source history)", but FY2023 does not, and there is no statement of what is missing.
- "last updated September 22, 2026" against September 23 on the award tab.
- "Distinct File C-linked awards … (not new awards)" is a good label.
- Commerce "File C / net −7.1%".
- "File C / net is 30.3%" appears in the footer, while the cards say "20.7% of net" (FY26). The two are consistent, since one is full history and one is FY26, but they are easy to confuse.

### sentinel: "Funding-action sentinel"

**(a)** There are 176 possible funding actions, 174 of them unreviewed. Two are confirmed terminations: DOE's October 2025 "Termination of 223 Projects, Saving Over $7.5 Billion" and NSF's 1,667 terminated awards. NOAA shows repeated large negatives across thousands of awards every month since November 2025: NMFS −$520M, NOS −$470M, OAR −$337M, NWS −$228M.

**(b)** "NOAA has cancelled roughly $1.7B across 5,000+ awards in FY2026, and the confirmed NSF/DOE terminations cost nothing ($0)."

**(c)**
- The confirmed-event cards put "**$0 gross negative · $0 net**" in the header position, next to "Saving Over $7.5 Billion".
- The NSF card pairs "$0 gross negative activity" with "**1,667 award IDs with negative entries**", a direct contradiction.
- "−$520M net" (sentinel) against "NMFS $520M" (ORF page) uses the word "net" for two different measures, with opposite signs.
- The boilerplate "The sign and amount do not establish a cancellation" appears roughly 100 times. This dilutes the message and doesn't explain what else the pattern could be.
- Source freshness shows "current" for snapshots dated 2025-06-05 and 2025-10-01.

**(d)**
- The same OCED program appears as three episodes.
- Weapons Activities is flagged with "$1.981B net" positive.
- "1 award IDs" (grammar).
- Raw ISO timestamps with microseconds.
- Each episode has a single "Open a linked USAspending award" link, even for 1,769 IDs.
- "Show 154 more unreviewed episodes": 20 of 174 are visible.
- The "Estimated pilot burden" table and its internal-process note ("…without delaying publication, account fan-out, or closing this implementation phase") appear on a public page.
- Every visible episode is FY2026. The FY2025 $5.03B NIST deobligation noted on the NIST page, and Army's −$32B, do not appear among the visible episodes.

### obligations-account-dod-navy-rdte: "Research, Development, Test, and Evaluation, Navy"

**(a)** Navy RDT&E obligated $28.1B through July, already above FY25's full year ($27.885B). Almost none of it (122 awards, −0.2%) is traceable to public awards. The DoD note explains why.

**(b)** "Navy R&D is growing fast and basically untraceable." Alternatively: "Basic Research got $570M with zero awards, so the money went nowhere."

**(c)** The top-recipients table is headed "Top recipients of award-attributed obligations", but #1 is "HII MISSION TECHNOLOGIES CORP $1.7M" in a $28.1B account. Without the DoD note in view, the ranking implies these are the main recipients. "File C portion … (−0.2% of net) −$43.1M" is a negative award share, which is confusing.

**(d)**
- Program-activity row "Undistributed $4.4M −653.2% 64".
- "System Development and Demonstration $7.031B −0.0%".
- The period chart spike of about $7.5B in 2023 is clipped at the top.
- The FY26 cumulative line ends above every other year at July, with a final step of about $2.6B.

### obligations-account-dod-defense-wide-rdte: "Research, Development, Test, and Evaluation, Defense-Wide"

**(a)** Defense-Wide RDT&E is surging: $44.9B through July, against $38.1B for all of FY25. The partial FY26 bar is the tallest on the chart. Lockheed Martin and Palantir are top recipients.

**(b)** "A record R&D surge in 2026", read as science spending. It is largely development and prototyping ("Advanced Component Development and Prototypes $11.361B"), plus "Basic Research $7.932B 0.0% 0" with no traceable award.

**(c)**
- The pale "'26*" bar is taller than every full year, which invites a surge reading before the year is complete.
- "LOCKHEED MARTIN CORPORATION" appears twice in the top 10 (#1 $275M and #6 $27.4M).
- The same NGI award appears as "+$311M" and "−$206M" in P03, which reads as a large cancellation.

**(d)**
- The period chart has a −$1.9B step (about 2024P08) followed by about +$9B.
- The latest period, "$8.462B", is the highest value in the series.
- Program-activity rows include "UNIDENTIFIED", "CLOSED ACCOUNT ADJUSTMENT", "RECERT OR LIMITED LIAB" and "DOD/VA INCENTIVE FUND", all at $0.

### obligations-account-dod-defense-health-program: "Defense Health Program, Defense"

**(a)** A $41B-a-year "science" account.

**(b)** That DoD spends about $41B a year on health science. The program-activity table shows "Operation and Maintenance $37.974B", which is health-care delivery. RDT&E is $1.505B.

**(c)** The account's presence under "Federal science obligation dashboard" and its roll-up into DoD's $206B. The top recipients (BCG Federal, Peraton "ENTERPRISE IT SERVICES INTEGRATOR", "AWS CLOUD SERVICES-COMMERCIAL", "PATIENT APPOINTING SERVICES") show it is not research.

**(d)**
- "BASIC RESEARCH $0 — 0" and "APPLIED RESEARCH $0 — 0" read as zeroed research.
- The same BCG task order appears as +$60.0M and −$13.7M in the same period.
- The period peak of about $12B around 2026P01 is unannotated.

### obligations-account-doe-sc: "Office of Science"

**(a)** DOE Office of Science is on a normal pace: $7.717B through July, in line with prior years at the same point. 90.7% of it is traceable to awards, mostly national-lab contractors. There is a large negative on the Jefferson Lab contract.

**(b)** "DOE cut $107M plus $42.3M from Jefferson Lab." The two negative flows are the same award ("TAS::89 0222::TAS MANAGEMENT AND OPERATION OF THE THOMAS JEFFERSON NATIONAL ACCELERATOR FACILITY."), and the sentinel lists both as episodes.

**(c)**
- "Source label unavailable (PARK 63YPT7L1YUJ) $656M 100.0% 306": a $656M line with no name.
- "IP — Isotope R&D and Production $169M 0.0% 0": a large line with no traceable award.

**(d)**
- Period chart spikes run past the top of the y-axis.
- The minus sign wraps onto its own line ("−" / "$42.3M").
- Otherwise the page is coherent. It is the cleanest account page I read.

### obligations-account-commerce-nist-its: "Industrial Technology Services"

**(a)** NIST ITS briefly obligated about $5.7B in FY25 and then clawed back $5B. FY26 is the biggest year yet ($1.011B, mostly CHIPS).

**(b)** "The government cancelled $5B of CHIPS awards in August 2025", or "NIST manufacturing funding hit a record in FY26".

**(c)**
- The cumulative-line form turns a single-period deobligation into a visual cliff from about $5.7B to $0.72B.
- The note ("the source reports a net deobligation of $5.03 billion…") is accurate. It does not name the program activity or say whether this was restructuring, correction or cancellation.
- "CHIPS $900M −0.0% 3" has no visible recipient in the top 10, which are all MEP centers of about $3–8M each.

**(d)**
- The period chart has +$5.7B around 2025P04 and −$5.0B around 2025P11, with a "see note" marker.
- The '26* partial bar is the tallest.
- Duplicate program-activity naming: "MEP — Hollings Manufacturing Extension Partnership $101M" and "ITS: Hollings Manufacturing Extension Partnership $3K".
- "PROGRAM ACTIVITY NOT SPECIFIED (PARK 0)" and "NIST Carryover (Summarized) Balances" appear as $0 rows.

### obligations-account-commerce-noaa-orf: "Operations, Research and Facilities"

**(a)** NOAA ORF obligated $3.651B through July, below FY24 and FY25 but on par with FY22 and FY23. Award-linked File C is **negative** (−$655M, "−17.9% of net"). Most NOAA line offices show negative File C ratios (NOS −154.6%, NESDIS −202.9%).

**(b)** "NOAA is clawing back hundreds of millions from its grantees." The negative File C is paired with a +$4.305B residual. The page's largest single negative award flow is only −$9.2M, so no large individual cancellations are visible here.

**(c)**
- "File C portion … (−17.9% of net) −$655M" as a headline card.
- Negative percentages for NWS, NMFS, NOS, OAR and NESDIS read as cuts to those offices.
- "ARPA-C $1.474B" is an acronym with no expansion.
- "Source label unavailable (PARK 5Q0283FWZJM)".

**(d)**
- The FY24 cumulative line is missing: only the label "FY24 · $7.250B" appears.
- The FY25 line starts at about $2.0B in December and has hollow points.
- The period chart has a single step of about $7.2B at "2024P12". Its tick labels jump from "2023P09" to "2024P12".
- The y-axis runs symmetrically to −$8B although the only negative is about −$0.1B.
- The FY bars show a real rise to $7.5B (FY25) and '26* at $3.65B.

### obligations-account-dhs-cisa-rd: "Research and Development, Cybersecurity and Infrastructure Security Agency"

**(a)** CISA's R&D account has effectively been shut down. It fell from $16M (FY19) to $3.3M (FY24) to "$98" (FY25), with $792K in FY26.

**(b)** "CISA's research budget was eliminated in 2025." The note properly hedges that "Source figures alone do not show whether the activity ended or moved to another account."

**(c)**
- The FY bar chart's near-zero '25 bar is a visual collapse. The hedge sits in a notes box below the chart.
- The label "FY2025, period 12" for a statement about annual totals is odd.

**(d)**
- The FY23 cumulative line spikes to about $12.9M in January and falls to about $1.0M in February. The note explains this: "the source's period 3 snapshot reported cumulative net obligations of $12.90 million…".
- The period chart has a paired +$12.9M / −$12M step.
- Top recipients: "No File C rows linked to public awards in FY2026. ▸ Show 3 more recipient rows".
- Program-activity names such as "CAS - INFRASTRUCTURE SECURITY R&D" use uppercase with an unexplained "CAS" prefix.

### obligations-account-nsf-rra: "Research and Related Activities"

**(a)** NSF R&RA is far behind pace: $3.794B through July against about $7.4–7.7B in full prior years. It was about $2.2B at June against about $3.3B a year earlier. Recipients look like normal science institutions.

**(b)** "NSF research funding is down about 50% this year." The '26* bar is about half the height of full years. Prior years obligate about 40% in August and September, so the true gap at P10 is smaller (about $3.8B against about $4.4–4.8B).

**(c)**
- The pale '26* partial bar sits next to full-year bars. The cumulative chart is the right comparison, but the FY bar chart invites a like-for-like reading.
- "USARC — Arctic Research Commission −$384K" in red.
- "ARP — American Rescue Plan Act $407K −1402.4% 162".

**(d)**
- The period chart is near $0 for 2025P12–2026P02.
- The "Unknown / other $0 — 0" row links to a page that claims "72,755 distinct linked awards".
- "Other Unmapped $13.8M 0.0% 0".

### obligations-account-nasa-science: "Science" (NASA)

**(a)** NASA Science obligated $5.287B through July. It trailed prior years for most of FY26 and caught up at P10. Caltech/JPL dominates.

**(b)** "NASA science is running well below prior years." That is true until P10, when a step brings it level with FY22.

**(c)**
- The H1 is just "Science — obligation dashboard".
- The page is identical in every figure to its single child page, "Science (Direct)".
- Caltech appears as both #1 ($1.419B) and #9 ($65.9M) with no explanation.

**(d)**
- The duplicated page.
- The sentinel's NASA episode "−$26.1M gross negative" against this page's "Negative ledger entries −$93.8M" is not reconciled.

### obligations-account-usda-nifa-research-education: "Research and Education Activities, National Institute of Food and Agriculture"

**(a)** NIFA research and education fell sharply in FY25 (to $797M from $1.215B in FY24 and $1.547B in FY23). FY26 ($721M) is slightly ahead of FY25's pace. Land-grant universities are the main recipients. The negative flows are explicitly tied to prior-administration awards.

**(b)** "USDA is terminating land-grant research awards made under the previous administration." This is the reading the negative-flow titles invite (see finding #7).

**(c)**
- Award titles "** AWARDS ISSUED PRIOR TO JANUARY 20, 2025, WERE FUNDED UNDER PREVIOUS ADMINISTRATIONS AND MAY NOT REFLECT THE PRIORITIES AND POLICIES OF T…" on four of the five "Negative entry" rows.
- The program-activity list contains dozens of $0 rows. Some carry awards ("ALFALFA FORAGE AND RESEARCH PROGRAM $0 — 3"), and names repeat ("OTHER UNMAPPED", "PROGRAM SUPPORT" and "SET ASIDE" each twice).

**(d)**
- "VETERINARY MEDICAL SERVICES ACT $40K −1061.4%" and "SET ASIDE 1500 $11K −4867.5%".
- The escaping artifact "NCA<(>&<)>T".
- A period spike of about $480M at 2023P06, which drives the tall FY23 bar and is unannotated.

### obligations-account-epa-science-technology: "Science and Technology" (EPA)

**(a)** EPA Science & Technology is well behind pace: $498M through July, the lowest line all year, against about $750–880M in full years. Many named research programs show $0.

**(b)** "EPA has zeroed out its research programs (air/climate, water, chemical safety, human-health risk assessment) in FY2026."

**(c)**
- About 70 "$0 — 0" program-activity rows with no statement that they are historical or renamed codes (finding #3).
- The negative flows are all university research grants ("DESCRIPTION:THE GOAL OF THE PROJECT IS TO ENGAGE S.E. QUEENS RESIDENTS IN THE MEASUREMENTS OF KEY AIR POLLUTANTS … −$707K"), which invites a "research grants cancelled" reading. The amounts are small.

**(d)**
- Duplicate program-activity names ("PESTICIDES: …", "IT / DATA MANAGEMENT", "FACILITIES INFRASTRUCTURE AND OPERATIONS", "REDUCE RISKS FROM INDOOR AIR").
- The typo "WATER QUALITY RESEARCH ADN SUPPORT GRANTS" next to the correct spelling.
- The page is very long (6,289 px) because of the $0 rows.

### obligations-account-va-medical-prosthetic-research: "Medical and Prosthetic Research"

**(a)** VA research is steady (about $1B a year). FY26 is on pace. No award detail is published.

**(b)** "$8.8B of VA research went to zero identifiable recipients", read as opacity or misuse.

**(c)** "$8.782B net obligations across 0 distinct linked awards" appears with no VA-specific note. DoD pages get one; VA does not.

**(d)**
- Duplicate program-activity codes: "MILLION VETERANS PROGRAM (826) $77.6M", "MILLION VETERANS PROGRAM $0", "- 5YR $0", "5-YEAR (826) $0".
- Otherwise the page is clean.

### obligations-pa-dod-basic-research: "Basic Research" (Army)

**(a)** Army basic research is $417M through July, behind prior years, with no traceable awards in FY26.

**(b)** "Army basic research has gone dark: no awards this year." The cards show "0" awards and "File C portion … (0.0% of net) $0".

**(c)**
- The H1 omits "Army"; it appears only in the breadcrumb.
- "File C / net is 215.1%" for the full history sits next to 0.0% for FY26, and neither is explained.

**(d)**
- The FY26 cumulative line doesn't appear until January.
- The period chart has a trough at about $14M followed by a spike of about $125M around 2026P01–P02.
- "No File C rows linked to public awards in FY2026" appears alongside "Show 20 more recipient rows (FY2024–FY2026)".

### obligations-pa-doe-basic-energy-sciences: "Basic Energy Sciences"

**(a)** BES is on or ahead of pace ($2.075B through July, the top line through June). 98.8% of it is traceable to national labs and universities.

**(b)** Little room for misreading. At most, "ORNL is being cut", from four small negative ORNL rows (−$22.8M, −$13.6M, −$7.1M, −$6.7M) alongside +$236M and +$150M.

**(c)** Raw codes as titles: "IGF::OT::IGF TAS::89 0222::TAS M&O CONTRACT FOR BNL".

**(d)**
- The period y-axis runs to −$1B although there are almost no negatives.
- Otherwise the page is clean.

### obligations-pa-nasa-science-direct: "Science (Direct)"

**(a) and (b)** Same as the NASA Science account page, which is identical.

**(c)** Duplicate Caltech rows. The negative flows (CLPS CP-12 "−$13.6M", DUSTER "−$7.2M", VIPER "−$6.3M") could be read as Artemis-science cancellations. The amounts are small and the direction labels are neutral.

**(d)** The minus sign wraps in the CLPS row. The page is identical to its parent.

### obligations-pa-nsf-unknown-other: "Unknown / other" (NSF R&RA)

**(a)** Confusing. The page claims "$25K net obligations across 72,755 distinct linked awards", but every card is $0 and every chart is empty.

**(b)** That more than half of NSF R&RA's awards (72,755 of 132,226) have unknown or unaccounted obligations. Alternatively, that the data are broken.

**(c)** "File C / net is 100167255.7%" appears as if it were a meaningful statistic.

**(d)**
- The y-axes read "$0K, $0K, $0K, $0K, $0K".
- The only visible bar is '20, at about $24.5K.
- A third cumulative end-label is clipped.
- "File C portion, FY2026 to date (— of net)".

### obligations-pa-hhs-administration-for-strategic-preparedness-and-response

**(a)** ASPR (biodefense) obligated $2.149B through July, ahead of FY25's pace. The money goes to vaccine and antibiotic makers.

**(b)** "This is HHS science." It is largely procurement and stockpile: "AMOXICILLIN TRIHYDRATE 500 MG ORAL CAPSULES…", "BOTULISM ANTITOXIN", "TAS::75 0140::TAS CONSTRUCTION OF VACCINE MANUFACTURING FACILITY".

**(c)**
- The ALL-CAPS H1 "ADMINISTRATION FOR STRATEGIC PREPAREDNESS AND RESPONSE — obligation dashboard" is unlike every sibling.
- The breadcrumb "ASPR R&D/P" hints at procurement, but the page never says so.
- The history covers only "FY2024–FY2026 combined", so the three-bar FY chart ('24* partial) invites trend reading on thin data.

**(d)**
- The period axis starts at "2024P06", different from every sibling.
- Minus signs wrap.
- The "IGF::OT::IGF" title.

---

## Skim notes: pages that differ from their siblings

- **Army RDT&E**: see finding #4. The FY21 and FY22 bars are about twice the level of neighbouring years, FY22 has a −$32B period, and there is no notes box.
- **Air Force RDT&E**: see finding #13. The FY24 plateau has hollow points and is followed by a single $32B period (2024P11). Also "(Reimbursable) $4.099B −0.0%".
- **Space Force RDT&E**: the series starts in FY2021. There is no text explaining the shorter history.
- **NNSA Weapons Activities**: FY26 $27.388B already exceeds FY25 ($26.256B). The sentinel flags it as an unreviewed signal although its net is positive. It is a nuclear-weapons account presented as "science".
- **NNSA Defense Nuclear Nonproliferation**: this is the only page family using "no data yet" instead of "$0" ("National Technical Nuclear Forensics no data yet", "GTRI International Contribution no data yet"). Also "Ukraine Supplemental $3.2M 1818.4%". NSF STEM Education ("Low Income Scholarship Program no data yet") and OCED ("Clean Energy Demonstrations (IIJA) no data yet") also use "no data yet". The inconsistent vocabulary suggests that "$0" and "no data yet" mean different things, but the site never says what.
- **DOE OCED**: "Net obligations, FY2026 to date $15.7M", "Positive $628M / Negative −$612M", "File C portion … (−3881.2% of net) −$609M". The FY26 bar is about zero against FY25's $8.441B. This is consistent with the sentinel's DOE event, but the page doesn't link to it.
- **DOE EERE / Electricity**: surges driven by supplemental funding, then an FY26 cliff (finding #18). EERE has many "$0 — 113"-style rows (awards linked, $0 net).
- **DOE Fossil Energy / Nuclear Energy / OST-R**: "Source label unavailable (PARK 63YPT7KCME5)", "(PARK 63YPT7SABUB) $646M", "(PARK 5RMTTPEQCS)". These are unnamed program activities holding large sums. FE: "Unconventional FE Technologies $1K −28409.5%".
- **Commerce NOAA PAC**: "File C portion … (−10.8% of net) −$171M". NOS "−1513.3%", OAR "−657.1%". There is a period spike of about $2.3B at 2024P12, and the y-axis runs to −$3B with no negatives.
- **Commerce Census Periodic**: an FY20 decennial spike of about $6.6B, unannotated. "Negative ledger entries −$177M".
- **Commerce Census Current Surveys**: File C is 0.1%, and unlike DoD there is no low-File-C note.
- **Commerce NIST STRS**: FY24 ($1.296B) has a late jump. There is a "CHIPS" program activity with $116M.
- **DHS CWMD R&D**: a steady decline from about $175M ('17*) to about $22M ('25). There are many duplicated "CAS - …" $0 program activities.
- **DHS S&T R&D**: FY25 $272M and FY26 $169M, against $557M (FY23) and $465M (FY24). The y-axis runs to −$200M with no negatives.
- **DOE ARPA-E**: FY25 $211M against FY24 $519M.
- **ED IES**: FY25 $517M against FY24 $821M; FY26 $324M. The period line is near zero for 2025P04–P09 and unannotated. Its Unknown/other page shows "10204.0%".
- **HHS AHRQ**: FY25 $299M and FY26 $184M, against about $370–398M earlier.
- **NASA Space Technology**: FY26 $426M against about $1.1B.
- **NSF MREFC**: the top-recipient list has only 8 rows, including "UNIVERSITY CORPORATION FOR ATMOSPHERIC RESEARCH $0" and "BATTELLE MEMORIAL INSTITUTE −$1". Zero and −$1 "top recipients" look broken.
- **NSF STEM Education**: FY26 $294M against about $1.2–1.3B in full years; "Negative ledger entries −$242M".
- **USDA ARS Salaries & Expenses**: nine program activities all show exactly "30.3%" File C/net with about 2,010 awards each. This looks like one pool spread proportionally, which a reader would take as nine separate portfolios. Also "SALARIES AND EXPENSES (REIMBURSABLE) $54.8M 120.9%" and "PENDING MAPPING $0".
- **USDA ARS Buildings & Facilities**: an unannotated FY20 spike of about $780M.
- **USDA ERS**: the card "File C portion … (1.7% of net) **$1000K**" is a formatting slip; it should read $1.0M. Also "(REIMBURSABLE) $254K −149.8%".
- **USDA NASS**: FY26 $103M, below every prior year all year (prior full years about $242–262M), unexplained.
- **USDA NIFA Extension / Integrated**: large negative ratios ("FARM STRESS ASSISTANCE NETWORK $23K −9257.9%"). The Integrated account's FY25 is $50.2M against FY24 $176M. Program-activity names repeat. Y-axes run to −$200M and −$400M with no negative values.
- **USDA Forest & Rangeland Research**: "FRR BIPARTISAN INFRASTRUCTURE LAW $14.4M −0.0%".
- **DOI USGS SIR**: "RESTORATION … (HURRICANE SUPPLEMENTAL P.L. 115-123) $2 0.0%". A $2 row renders as if it were meaningful.
- **Unknown/other program-activity pages**: DOI and DOT are entirely empty ("$0 net obligations across 0 distinct linked awards"). Commerce: "$2.507B … across 23,892", with FY22 and FY23 cumulative lines negative and "314.9%". DHS: "3298.9%". EPA: FY25 cumulative line ends at about −$201M, driven by a single period of about −$200M. USDA: "$803M … across 5,083", almost all '17*. VA: "$655M … across 0 distinct linked awards".
- **Every account page** repeats the intro "USAspending File B and File C. Signed obligations attributed by reporting period — not award totals, appropriations, or outlays." The terms File B and File C are never defined in plain language on any page I read.

---

## Coordinator dispositions (2026-09-23)

The review covered the release screens pack of the integration head `a826fc3`
(all eleven items plus the #88 data fix). Registry 380/380, fast 7/7,
rendered 4/4, and screens 74/74 on that head.

**Gate reasoning.** Rule 5 says High findings gate release. The coordinator
checked each High against the screens pack captured on `main` (`c356a78`)
at the start of Stage 2. None of the seven Highs was introduced or made
worse by a Stage 2 change: each is live on `main` today. The W17
precedent applies (a pre-existing High is dispositioned and routed, not
treated as a block on an unrelated release). Stage 2 itself removes several
earlier misleading readings: the partial-month cliff, the Navy −$25B period
row (#88), the raw red banner, sloped period lines, the unlabeled all-years
total, and obligation figures on the award tab. Holding it would keep those
on `main` without fixing any of the seven. Stage 2 therefore ships once the
agent-owned fixes below land and re-verify green. Every owner-layer finding
goes to the owner as one follow-up memo (Stage 2b), with a recommendation
for each.

| # | Sev. | Disposition |
|---|---|---|
| 1 | High | Pre-existing (scope of the registered accounts; decision layers a/c). **Owner memo 2b-1**: recommend a scope disclosure in the landing subtitle. A research-only subtotal would be a measure change. |
| 2 | High | Pre-existing (NIH obligation accounts are out of registry by the Phase 3.2d scope). **Owner memo 2b-2**: recommend "NIH accounts are not included here" on the landing and the HHS row. |
| 3 | High | Pre-existing. **Fixed in part (agent-owned, display only):** on account pages, program activities with $0 current-FY net obligations fold into a collapsed "Show N program activities with $0 net obligations in FY2026" group below the active ones. No new claim; the rows stay available. Any explanatory wording ("retired or renamed code") would be a claim about the source's coding, so it goes to the **owner memo 2b-3** (recommend no claim). |
| 4 | High | Pre-existing. Data check done: the Army RDT&E FY totals match GTAS/File A pins exactly (FY2021 $56.496B, FY2022 $52.527B). The FY2022 path is P06 $31.0B → P07 $74.0B → P09 $81.7B → P10 $49.9B → P12 $52.5B: a three-period plateau, then a 39% fall. It is below the >50% drop check and does not revert at the next period, so neither acceptance rule fires. Whether it is a source-snapshot anomaly needs a CI re-pull (data work, outside Stage 2). **Owner memo 2b-4**: recommend the re-pull, then a source-figure note if confirmed. |
| 5 | High | Pre-existing sentinel wording (decision-5 header figures on source-only episodes). **Owner memo 2b-5.** |
| 6 | High | Pre-existing sentinel wording (the sentinel's File C "net activity" vs the ledger's File B net). **Owner memo 2b-6.** |
| 7 | High | Pre-existing (source award descriptions rendered as titles; public-claim risk). **Owner memo 2b-7**: recommend rendering descriptions as attributed source text. |
| 8 | Med | Pre-existing (Oct–Nov 2025 low counts). Any caption naming a cause is a claim. **Owner memo 2b-8.** |
| 9 | Med | Pre-existing (the root H1 vs NIH/NSF coverage; the decision-4 coverage line exists). **Owner memo 2b-9.** |
| 10, 11, 23 | Med/Low | Pre-existing (inactive NSF admin offices; NIH units with no awards; BFA pages). Recorded for a later batch; no Stage 2 change. |
| 12, 24 | Med/Low | Owner-approved notes (NIST ITS; CISA from Stage 2 item 8). No change. |
| 13 | Med | **Fixed (agent-owned, item 1's domain):** a covering step is labeled with the span it absorbs ("covers P05–P11"), so it no longer reads as a one-period surge. |
| 14, 15, 16, 19, 20, 21, 25, 26 | Med/Low | Pre-existing and disclosed on-page (the partial-year "*", the signed-ratio note, "Unknown / other" semantics, sentinel counting, source recipient and title strings). Recorded; no Stage 2 change. |
| 17, 28 | Med/Low | Sentinel-facing wording (the "current" source status and raw timestamps; the pinned "Replace them with measured figures after eight weeks" line). **Owner memo 2b-10.** |
| 18 | Med | Cause attribution (supplemental or one-time money). **Owner memo 2b-11**: recommend no change now. |
| 22 | Low | **Fixed in part:** the mechanism-chart end labels were clipped ("28776 continuin"); they now use a formatted number and a wider margin. The duplicated "7 awards…" line is two pipeline notes (root and NSF), shown verbatim per the item-10 decision; no change. "Full fiscal years" including the partial '26* is pre-existing, recorded. |
| 27 | Low | **Fixed in part:** a minus sign no longer wraps in numeric cells (`white-space: nowrap`). The NOAA ORF FY24 single-point line and the axis jump are W14's null-hiding and omitted-period design; no change. |
| page note | Low | "107 · Sep 2026 to date" overlapping the line (item 11): **fixed**. The label now sits above the higher of the last two points. |
