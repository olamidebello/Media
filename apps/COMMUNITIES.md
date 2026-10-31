# Africa Media Hub communities

This release adds community features to the existing user-owned station system. It is an Africa Media Hub implementation, not a connection to Twitch or a claim of compatibility with Twitch accounts, Bits, subscriptions, APIs, extensions or creator programs.

## Deploy

On the existing Media server:

```sh
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-community.yml
```

The play imports the existing application updater, backs up the database, initializes community tables, updates the web interface, restarts the application, and checks assets, access restrictions and public HTTPS. It does not restart or reconfigure the station engine, change TCP ports, build native packages, enable payment gateways, or grant creator monetization eligibility. Deploy `deploy-stations.yml` separately if the RTMPS/HLS engine is not yet installed.

Open **Community** for discovery, follows, notifications, and payment verification. Open **Build a Station → Community dashboard** for creator controls. Channel owners and assigned moderators can also enter the dashboard from a channel watch page. Choose a standard profile; independent communities are excluded from Kids-profile API requests. Approved public watch links and embeds are public and are not a parental-control boundary.

## Feature coverage

| Area | Implemented behavior |
| --- | --- |
| Broadcasting | Existing authenticated OBS/hardware-encoder RTMPS → HTTPS HLS; webcam, screen, gameplay, microphone and scene production through the encoder |
| Categories | Station category, stream title and comma-separated tags; Gaming, Just Chatting, Music, Sports, Creative, News, Education and Entertainment discovery filters |
| Discovery | Text search, category/tag filtering, followed channels and a deterministic following/live/popularity ranking; approved offline channel profiles remain available |
| Chat | Three-second polling, replies, @mentions, custom image emotes, public handles/profile pictures, broadcaster/moderator/member badges, pinned messages and built-in commands |
| Community | Follow/unfollow, opt-in in-app broadcast notices, mention notices, notification inbox, optional ten-minute raid invitation links |
| Memberships | Verified prepaid 30-day channel passes, gifts to an existing community handle, member badge and members-only chat benefits; no automatic renewal |
| Cheers | One-time verified support payments; no purchased virtual currency or Twitch Bits balance |
| Channel Points | Free non-cash points, timed signed-in viewing heartbeats, creator-created rewards, fulfillment and idempotent point refunds |
| Interaction | Polls, free-point predictions, voting locks, explicit outcome settlement/cancellation, !help, !schedule and !points commands |
| Video library | Creator-supplied recording URLs, past-broadcast/highlight/featured listings, timestamp-range clips and shareable clip links |
| Sharing | Channel links, clip links and embeddable approved public live players |
| Creator tools | Existing stream keys/output control/schedule/graphics plus community identity, emotes, moderators, activities, library, offers and bot keys |
| Analytics | Last 30 UTC days of measured signed-in viewing sessions/watch time/peak active viewers, follower counts and verified gross payments by currency |
| Monetization | Operator-approved membership/support offers; labeled sponsorship panels; existing platform display advertising remains separate |
| Moderation | Channel moderators, held-message review, blocked terms, slow mode, followers-only/members-only chat, pin/delete, timeouts and bans |
| Safety | Existing authenticated sessions/CSRF controls, account suspension, reports to platform administrators, user blocking/unblocking and scoped bot keys |
| Collaboration | Opt-in raids, channel moderator collaboration and existing external encoder production workflows |
| Customization | Station logo/banner, title/tags, public chat avatars/handles, information/sponsor panels, emotes and member badge label |
| Accessibility | Native playback controls, keyboard-disclosable navigation, semantic forms and optional creator-provided WebVTT captions |
| Devices | Responsive existing web/native-WebView application and compatible HLS players; available controls depend on the device/browser |
| Developer tools | Station-scoped bearer keys for public chat/event polling and bot messages, cursor parameters, expiration and revocation |

## Important distinctions

Chat uses bounded HTTP polling, not WebSockets. Public chat reads return the most recent 100 messages plus an older pinned message when applicable. Links and repeated-character messages are held by a simple rule-based filter; this is not Twitch AutoMod or a guarantee of abuse detection. Chat expires after 30 days. A public handle is required for participation; default handles are `viewer` followed by the account ID. Names matching another account's default handle are reserved. Mentions notify at most five distinct recipients per message, and blocking suppresses those notifications.

Notifications are an in-app inbox, not background push, SMS or email. A broadcast notice means the creator enabled output; viewers must check whether an actual encoder signal is available. Browser tabs need to be open for chat/activity updates. Raids are voluntary links, not forced redirects or automatic viewer transfers.

Points are free engagement counters with no cash value and no purchase, transfer, withdrawal or financial prize. The client sends heartbeats only while signed in, visible and playing. The server enforces timing, a fresh local live signal or an enabled external source, account identity and balance checks; it cannot prove human attention or prevent all multi-account farming. Each minute of continuing accepted heartbeats may award ten points. Predictions deduct stakes once, reject duplicate votes, and settle once after the deadline. Cancellation or no winning stakes refunds stakes. Winning shares use integer division; rounding remainders are not awarded. Reward rejection refunds the recorded point cost once.

Recordings are supplied by the creator as authorized HTTPS media URLs. This release does not automatically archive live output, store uploaded video files, transcode content, produce exported clip files, or run automatic playout. A clip is a shareable timestamp range within an existing recording. Captions must be supplied by the creator as WebVTT or supported in the source; there is no automatic speech transcription. Cross-origin media/caption sources must permit browser playback/CORS.

Viewing analytics count signed-in clients with accepted heartbeats. They exclude anonymous viewers, are not audited unique-person counts, and are not a load-tested capacity claim. External stream health remains unverified. Gross payment totals are neither net income nor an available payout balance.

## Channel payments

Owners may prepare up to ten membership/support offers. An offer is hidden from the general Marketplace and cannot be purchased there as an ordinary active product. The channel checkout binds its station, beneficiary and benefit to the order **before** the provider checkout is created. Customer-supplied completion claims do not activate benefits.

Payment availability requires all of:

1. Existing Stripe or Paystack secret configured server-side using the platform's payment settings.
2. That gateway enabled and recognized as a live key. Community purchases reject test-mode gateways; fixtures test this flow without real transactions.
3. A super administrator enables creator eligibility in **Admin → Creator payment eligibility** and documents an operator-managed creator settlement arrangement without bank credentials.
4. The station remains approved and its owner active.

Checkout uses a one-time payment, including for memberships. After paying, verify the order under **Community → Channel payments & gifts** or Marketplace. The server retrieves payment status from the provider and verifies its reference, amount and currency before applying the benefit. Repeating verification does not extend a pass twice. Gifts are delivered to the existing handle's account. Memberships extend the later of now or the current expiry by 30 days. Refunds/chargebacks do not automatically reverse these benefits; an administrator can revoke membership after operator review.

Payments are collected by the configured platform merchant account. Automated creator payouts, payout wallets, subscription renewals, provider webhook processing, chargeback synchronization, refunds, tax calculation and financial reconciliation are **not provided by this release**. The platform operator must arrange those operations before enabling creator payments. Enabling eligibility is not proof of that arrangement. Do not enable monetization merely to test the UI on a live gateway. No gateway settings are changed by deployment.

Provider references: [Stripe fulfillment guidance](https://docs.stripe.com/checkout/fulfillment), [Paystack verification](https://paystack.com/docs/payments/verify-payments/). This implementation intentionally requires explicit verification; it does not claim reliable background fulfillment without webhooks.

## Scoped bots and public events

Create a key in **Community dashboard → Payments & developer tools**. The key is displayed once, stored as a SHA-256 hash, expires after 30 days, and may be revoked at any time. Maximum five keys per station and thirty API requests per key per minute; chat message limits also apply. Keys cannot access unapproved/suspended channels, moderator queues, private payout notes, stream keys, points, purchases or moderation actions.

```sh
curl -H 'Authorization: Bearer YOUR_SCOPED_BOT_KEY' \
  'https://media.africandroid.world/api/community/bot?after=0&event_after=0'

curl -X POST -H 'Authorization: Bearer YOUR_SCOPED_BOT_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"action":"message","message":"Welcome to the channel"}' \
  https://media.africandroid.world/api/community/bot
```

Responses contain public chat and the last retained public channel events, including chat, broadcast-enabled, poll/prediction, raid, settlement and verified-support events. Store the highest returned message and event IDs for the next poll. Up to 1,000 events are retained per station. Bots post as Station bot. No user-supplied JavaScript executes on the platform. Arbitrary third-party extensions, OAuth developer applications, outbound webhooks and a Twitch-compatible API are not included.

## Validation

Unit/API fixtures cover cross-account authorization, CSRF/Kids restrictions, held chat and bans, private-state redaction, follows/notices, timing-controlled points, duplicate votes/settlements/refunds, safe media URLs, scoped bot revocation, incorrect payment totals, gift membership delivery and idempotent benefit activation. Payment tests mock provider APIs; no real card is charged. Complete real-device playback, multi-user chat and configured-provider acceptance tests after deployment before a public launch.
