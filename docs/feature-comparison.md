# Feature and security-defense comparison

Versions: Keycloak 26.8.1, authentik 2026.8.5 (open-source core), Authelia 4.39.28, LLDAP 0.6.3 (Authelia's user directory in this benchmark), Zitadel v4.20.0, Rauthy 0.37.2, Ory Hydra v26.2.0 + Ory Kratos v26.2.0 (open-source editions), Casdoor v4.24.0, Logto v1.45.0 (open-source edition), Dex v2.46.1, Kanidm 1.11.2 and Pocket ID v2.19.1. Researched on 2026-10-27 from official documentation, release notes and the source code at each release tag.

How to read the cells:

- "Default" means a fresh install with the shipped configuration. Numbers in brackets point to the Sources list at the end, which is grouped by product.
- "unknown" means it could not be confirmed from the docs or the source. It does not mean "no".
- "(Enterprise)", "(Cloud only)", "(OEL)" (Ory Enterprise License) and "(Ory Network only)" mark features that the open-source edition does not include.
- The Authelia and LLDAP columns each describe that product on its own. Ory Hydra and Kratos share one column, and "(Hydra)" or "(Kratos)" names the component that provides a feature.
- Where the documentation and the code disagree, the cell follows the code at the tag.

## 1. Protocols

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| OIDC provider | yes, OpenID Provider; OIDC Core and Discovery certified (18.0.0); per-realm discovery and ID tokens [1, 2, 3, 4] | yes, OAuth2 provider acts as an OIDC OP; OpenID Certified OP profiles as of 2026.8 [166, 167, 168] | yes, OpenID Certified OP (Basic, Implicit, Hybrid, Form Post, Config); labelled beta; off until configured [276, 277, 278] | no (LDAP directory only; README says add Keycloak/Authelia for OAuth/OpenID) [378, 379] | yes, OIDC OP with discovery, userinfo, JWKS; code+PKCE, implicit, refresh, JWT profile grants [444, 445, 446] | yes, OIDC OP with discovery, ID tokens (EdDSA or RS256-512), auth code flow with PKCE [562, 563] |
| OAuth2 client credentials | yes, per client: confidential client with Service account roles enabled (off for new clients) [5, 6, 7, 8, 9] | yes, client_credentials grant; client sends username + app-password token, provider secret, or federated JWT [166, 169] | yes (client_credentials grant, since 4.38.0) [279, 280, 281] | no (not an OAuth2 server) [378, 379] | yes, for service accounts (machine users) with a generated client secret, not for app clients [446, 447, 448, 449] | yes, client_credentials for confidential clients (flow enabled per client) [562, 564] |
| Device authorization grant (RFC 8628) | yes, supported, feature on by default; per-client Device Authorization Grant switch off by default [3, 10, 11, 12, 13, 14, 15] | yes, RFC 8628; needs a device code flow set on the brand (none shipped); device endpoint 20 req/h per IP [170, 171] | yes (device_code grant and /api/oidc/device-authorization, since 4.39.0) [279, 280, 281, 282, 283] | no (not an OAuth2 server) [378, 379] | yes, /oauth/v2/device_authorization; user code valid 5 min by default; Login V1 and V2 both handle it [446, 450] | yes, RFC 8628 device grant at /oidc/device; per-IP start rate limit off by default [562, 565, 566] |
| Token exchange (RFC 8693) | yes: V2 GA internal-internal; V1 preview+deprecated adds external tokens, impersonation; delegation preview [10, 16, 17, 18, 19, 20, 21, 22] | yes, 2026.8, GA, off by default: authentik + external OIDC-source subject tokens; OBO needs Enterprise agents [168, 172, 173, 174, 175, 176] | no (RFC 8693 not supported; grant type listed as planned) [279, 280, 282, 284] | no (not an OAuth2 server) [378, 379] | yes, GA: Zitadel-issued tokens (downscope/audience), impersonation (opt-in setting); no third-party IdP tokens [451, 452, 453, 454, 455] | yes, GA since 0.36.1: impersonation and delegation (act); Rauthy access tokens only, opt-in per client [567, 568, 569, 570, 571] |
| SAML 2.0 IdP | yes, SAML 2.0 IdP for SAML clients (Redirect, POST, ECP); upstream SAML IdPs can also be brokered [23, 24, 25, 26, 27] | yes, SAML 2.0 IdP: Redirect/POST bindings, SP- and IdP-initiated SSO, SLO, metadata; SAML source for upstream [177, 178] | no (SAML 2.0 IdP is a roadmap item at the library-selection stage) [278, 285] | no (no SAML in source; SSO protocols left to Keycloak/Authelia etc.) [378, 380] | yes, SAML 2.0 IdP (SP-initiated only, Redirect/POST bindings); upstream SAML IdPs also supported [456, 457, 458] | no (OIDC/OAuth2/PAM only; 'saml' appears in source only as RFC 8693 token-type URNs) [562, 563, 572] |
| LDAP server (serves LDAP to apps) | no, LDAP is only consumed as a user store; no LDAP server or listener in docs or source [28, 29] | yes, via LDAP outpost (LDAPS/StartTLS, bind and search modes, code-based MFA in bind password) [179, 180] | no (Authelia is only an LDAP client; no LDAP server or component) [278, 286, 287] | yes, built in: LDAP :3890 (LDAPS :6360 off by default); limited subset, simple bind only [378, 381, 382, 383, 384] | no (not in source; single HTTP/gRPC listener; LDAP only as upstream IdP) [459, 460, 461] | no (no LDAP code in source; own PAM/NSS modules are offered instead of LDAP for hosts) [573, 574] |
| LDAP/AD as a user source | yes, built-in LDAP/AD federation: import with sync, or no-import; password check via LDAP; Kerberos too [28, 29] | yes, LDAP source: user/group sync, LDAP password bind backend, optional password writeback; AD/FreeIPA guides [181, 182] | yes, LDAP/AD via service-account bind; presets for AD, FreeIPA, LLDAP, GLAuth, RFC2307bis; no sync [286, 288] | no (only a one-shot CLI import tool from OpenLDAP; no federation or sync) [378, 385, 386] | yes, LDAP/AD as external IdP: bind at login, attributes mapped to a Zitadel user [461, 462] | no (maintainer in #915: LDAP not planned unless contributed or requested as paid work) [574] |
| SCIM (inbound/outbound) | yes, inbound only: SCIM 2.0 Users/Groups API (GA in 26.8), per-realm switch off by default; no outbound push [12, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41] | yes, both: inbound SCIM source (/source/scim/&lt;slug&gt;/v2); outbound SCIM 2.0 provider (OAuth auth is Enterprise) [183, 184] | no (not in docs or source) [278, 289] | no (no SCIM endpoints; management via GraphQL or LDAP only) [380, 387] | partial, inbound SCIM 2.0 server per org (/scim/v2/{orgId}), Users only, no Groups; no outbound [463, 464, 465] | partial: outbound only (SCIM v2 client syncs users and groups to apps); no inbound SCIM server [563, 575] |
| RADIUS | no (not in docs or source: grep of 26.8.1 tarball for 'radius' only matches the phrase 'blast radius') [28] | yes, via RADIUS outpost: authentication only, PAP; EAP-TLS is (Enterprise) [185, 186] | no (not in docs or source) [278, 286] | no (only LDAP/LDAPS and HTTP listeners; no RADIUS) [388, 389] | no (not in source or docs; only an HTTP/gRPC listener) [459, 460, 466] | no (not in docs or source) [562, 563] |
| Forward-auth for reverse proxies | no, no forward-auth endpoint or proxy; docs only point to third-party mod_auth_openidc (unsupported) [42, 43] | yes, proxy provider forward-auth via embedded or standalone proxy outpost: nginx, Traefik, Caddy, Envoy [187, 188, 189] | yes, built in: /api/authz/forward-auth (Traefik, Caddy), auth-request (nginx), ext-authz (Envoy) [278, 290] | no (no forward-auth endpoint; docs pair LLDAP with Authelia/Authentik/Keycloak for that) [378, 380, 390] | no first-party forward-auth endpoint; docs point to third-party oauth2-proxy [466, 467] | yes, built-in: /oidc/forward_auth (Bearer) and per-client /clients/{id}/forward_auth with callback [576, 577, 578] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| OIDC provider | yes (Hydra): OpenID Certified (certified with v1.0.0); login and consent delegated to Kratos or a custom app [675, 676, 677] | yes, OpenID Provider with discovery and JWKS (global and per application); ID tokens RS256 by default [786, 787, 788, 789] | yes, OP mounted at /oidc, built on a Logto fork of node-oidc-provider 9.11.3 [921, 922, 923, 924] | yes, federating OIDC OP issuing signed ID tokens (RS256 default); docs: not fully Basic-profile compliant [1025, 1026, 1027] | yes, per-client issuer/discovery; ES256 ID tokens default (RS256 opt-in); PKCE S256 required by default [1118, 1119, 1120, 1121, 1122] | yes, OIDC OP: authorization code flow only (PKCE; query, fragment, form_post); ID tokens RS256 by default [1239, 1240, 1241] |
| OAuth2 client credentials | yes (Hydra), GA; enabled per client via its grant_types [676, 678, 679] | yes, per-app grant type; in console defaults for new apps, not enabled on app-built-in [790, 791, 792, 793, 794] | yes, for machine-to-machine apps (resource or organization_id required) [921, 922, 925] | yes, since v2.46.0, off by default: list in oauth2.grantTypes or set flag; confidential clients only [1028, 1029, 1030, 1031, 1032, 1033, 1034] | yes, confidential (client secret) clients only; token is an encrypted JWE; not listed in discovery grant types [1118, 1119, 1123, 1124] | yes, confidential clients only (client secret or federated JWT assertion); added in v1.11.0 [1239, 1242, 1243, 1244] |
| Device authorization grant (RFC 8628) | yes (Hydra): /oauth2/device/auth with verification UI hook; added in v25.4.0, before this pin [678, 680, 681, 682] | yes, RFC 8628 at /api/device-auth; off by default (needs Device Code grant and Device login sign-in method) [786, 791, 794, 795, 796] | yes, since 1.38.0; native apps opted into device flow (isDeviceFlow), public clients [922, 926, 927, 928, 929] | yes, on by default (in default grant list); /device/code endpoint; since v2.25.0 [1026, 1028, 1035, 1036] | no: stub code only, behind the non-default dev-oauth2-device-flow build feature (handlers return errors) [1125, 1126, 1127, 1128] | yes, /api/oidc/device/authorize; user code valid 15 min, 5 s polling interval [1239, 1240, 1245, 1246] |
| Token exchange (RFC 8693) | no RFC 8693 (open feature request #1218); only RFC 7523 JWT-bearer grant for trusted external JWTs (GA) [678, 683, 684, 685, 686] | yes, GA: internal tokens (downscope, audience) and trusted external OIDC tokens; no actor or impersonation [786, 794, 797, 798, 799] | yes, GA, per-app opt-in: impersonation tokens, PATs, Logto access tokens (delegation); no external tokens [929, 930, 931, 932, 933, 934, 935] | yes, external only: upstream ID/access token via OIDC or GitLab connector; no impersonation; on by default [1028, 1037, 1038, 1039, 1040, 1041] | yes, GA (1.9+): service-account API token in, OAuth2/OIDC tokens out; no actor/impersonation/external [1123, 1129, 1130, 1131] | no; not among supported grants or composed Fosite handlers (no RFC 8693 code) [1239, 1240] |
| SAML 2.0 IdP | no: neither acts as a SAML IdP; Kratos SAML login (SP side, upstream) is OEL/Ory Network only [687, 688, 689, 690] | yes, built-in SAML 2.0 IdP per app (metadata, redirect/POST, IdP-initiated, SLO); also SAML SP upstream [800, 801, 802, 803] | yes, SAML 2.0 IdP (SAML apps, SP-initiated); OSS capped at 3 apps without a paid self-hosted license [936, 937, 938, 939] | no (only consumes upstream SAML via a connector the README marks unmaintained) [1042, 1043, 1044] | no (not implemented; maintainers cite SAML security risks, issue #2025 open with no work started) [1132, 1133, 1134] | no; maintainers say Pocket ID is solely an OIDC provider; SAML-only apps need a third-party proxy [1247, 1248, 1249] |
| LDAP server (serves LDAP to apps) | no (not in docs or source; maintainers say LDAP is not planned) [691, 692] | yes, built-in LDAP server (bind and search) on port 389, listener on by default; LDAPS 636 only with a cert [804, 805, 806, 807] | no (open feature request; nothing in source or docs) [923, 940] | no (LDAP is only an upstream connector; no LDAP server in source) [1042, 1045] | yes, built-in read-only LDAPS (bind, search, compare, whoami); off by default until ldapbindaddress is set [1135, 1136, 1137, 1138] | no; docs: Pocket ID doesn't serve LDAP to other apps (LDAP is inbound sync only) [1250] |
| LDAP/AD as a user source | no: no LDAP/AD federation, sync or bind; not planned per maintainers (issue #274) [691, 692] | yes, sync users from LDAP/AD (manual or scheduled) and check their passwords by LDAP bind; one-way [808, 809, 810] | no (maintainer: no native LDAP connector planned; bridge via OIDC/SAML enterprise SSO) [941, 942, 943] | yes, LDAP connector (stable): bind plus user/group search per login, AD supported; optional Kerberos SPNEGO [1043, 1046, 1047] | partial: one-way import/sync via first-party tools (FreeIPA, RFC 4533 LDAP); no live bind or federation [1139, 1140, 1141] | yes, one-way LDAP/AD sync of users and groups, hourly, off by default; no LDAP password login [1250, 1251, 1252, 1253] |
| SCIM (inbound/outbound) | no: inbound SCIM server is OEL/Ory Network only; no SCIM code in OSS Hydra or Kratos [687, 693] | partial, inbound SCIM 2.0 server (Users, Groups) at /scim for admins; no outbound push (syncer only pulls) [787, 811, 812, 813, 814] | no (neither inbound nor outbound; maintainer says SCIM is on the roadmap) [944] | no (no SCIM server or client in source) [1042, 1048] | partial: inbound only, SCIM-based sync API for Kanidm's own sync tools; no RFC 7644 /Users, no outbound [1139, 1142, 1143] | partial: outbound only, pushes users and groups to each client's SCIM endpoint (v2.0.0+); no SCIM server [1254, 1255, 1256] |
| RADIUS | no (not in docs or source) [686, 694] | yes, built-in RADIUS on UDP 1812 (listener on); per-org Enable RADIUS off by default; default secret 'secret' [805, 806, 815, 816] | no (not in docs or source) [921, 923] | no (no RADIUS in source) [1042] | yes, via first-party FreeRADIUS module rlm_kanidm and the kanidm/radius container (separate component) [1144, 1145, 1146] | no (not in docs or source) [1247, 1248] |
| Forward-auth for reverse proxies | partial (Kratos /sessions/whoami: 200 + X-Kratos-Authenticated-Identity-Id or 401); Oathkeeper is separate [695, 696] | yes, built-in /api/forward-auth for Traefik, Caddy, nginx (needs a Site, since v4.20.0); Envoy not documented [817, 818, 819, 820] | no, Protected App (Cloudflare-based auth proxy) is Cloud only; no forward-auth endpoint in OSS [939, 945, 946] | no (no forward-auth endpoint; docs call Dex a protocol provider, not a gateway) [1042, 1043, 1044] | no first-party forward-auth endpoint; docs use third-party OAuth2 Proxy with nginx auth_request [1126, 1147, 1148] | no first-party component; docs point to third-party proxies (OAuth2 Proxy, Tinyauth, traefik-forward-auth) [1248] |

## 2. Tokens and sessions

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| Introspection endpoint (client auth needed) | yes, RFC 7662; confidential clients only (any client auth: secret, JWT, mTLS); public 403; caller must be in aud [10, 44, 45, 46] | yes, RFC 7662; confidential client creds only (client_secret_basic or \_post); own or federated tokens [166, 190, 191] | yes; client auth required (client_secret_basic default, post, JWT, private_key_jwt) or bearer AT; no none [282, 291, 292, 293, 294, 295] | n/a (not an OAuth/OIDC server) [378, 379] | yes, /oauth/v2/introspect; caller must be API/OIDC app with client secret (Basic) or private_key_jwt [468, 469, 470] | yes, /oidc/introspect; auth: Basic id:secret of any enabled client, or any valid Rauthy Bearer token [578, 579, 580] |
| Revocation endpoint (RFC 7009) | yes, RFC 7009 /revoke for refresh/offline and access tokens; only the client the token was issued to [10, 47, 48, 49, 50] | yes, RFC 7009 /application/o/revoke/; confidential clients authenticate, public clients by client_id [166, 192] | yes (RFC 7009 at /api/oidc/revocation; public clients may use auth method none) [282, 283, 291] | n/a (not an OAuth/OIDC server) [378, 391] | yes, /oauth/v2/revoke for access and refresh tokens; revoking a refresh token also revokes its access token [445, 471] | yes, /oidc/token/revoke (since 0.34.0); access tokens blocklisted by jti, refresh tokens deleted [562, 581, 582] |
| Access token format (default) | JWT only: signed JWS (RS256 default), optional lightweight JWT; no opaque access token format [4, 51, 52, 53] | JWT access tokens always (signed; JWE if encryption key set); no opaque option; refresh tokens opaque [166, 193, 194] | opaque by default (HMAC-signed, authelia_at\_ prefix); JWT (RFC 9068) opt-in per client [282, 296, 297, 298] | n/a (not an OAuth/OIDC server) [378, 392] | opaque by default; JWT selectable per app or per service account [472, 473, 474] | JWT only: access tokens are JWTs (header typ at+jwt, RFC 9068); no opaque option [583, 584] |
| Refresh-token rotation | partial: new RT per refresh, old stays valid; opt-in Revoke Refresh Token: 1 use, reuse revokes client session [54, 55, 56, 57, 58, 59] | yes, on by default: each refresh rotates, old token revoked; reuse rejected and logged; no family revoke/grace [166, 195, 196, 197] | yes, always on: used RT and its AT revoked; replay of old RT revokes the grant's tokens; no grace period [299, 300, 301] | n/a (not an OAuth/OIDC server) [378, 392, 393] | yes, always rotates; old token rejected at once; no reuse detection; no grace period; 30d idle, 90d max [475, 476, 477, 478] | yes, always on: used token deleted, new one issued; reuse rejected, no family revocation, no post-use grace [585, 586, 587, 588, 589, 590] |
| RP-initiated logout | yes, end_session_endpoint per realm (RP-Initiated Logout, certified); id_token_hint, post_logout_redirect_uri [1, 3, 60] | yes, per-app end_session_endpoint; id_token_hint needed with post_logout_redirect_uri; ends app session only [167, 198, 199] | no (RP-Initiated Logout not implemented; no end_session_endpoint) [282, 302] | n/a (not an OAuth/OIDC server) [378, 379] | yes, /oidc/v1/end_session with id_token_hint or client_id and post_logout_redirect_uri [445, 479] | yes, end_session_endpoint /oidc/logout (GET and POST) with post_logout_redirect_uri and state [562, 591, 592] |
| Back-channel logout | yes, Back-Channel Logout 1.0 (certified), per-client URL; front-channel also supported, default on new clients [1, 8, 60, 61, 62] | yes, back-channel (default method) and front-channel per provider Logout URI; docs page badged Preview [167, 168, 199, 200] | no (back-channel and front-channel logout not implemented; roadmap Beta 9) [282, 302, 303] | n/a (not an OAuth/OIDC server) [378, 384] | yes, Back-Channel Logout 1.0 with sid, per-app backchannel_logout_uri; front-channel not implemented [445, 480, 481] | yes, back-channel logout (logout tokens, up to 100 retries), also accepted from upstream; no front-channel [562, 591, 593] |
| PAR (RFC 9126) | yes, PAR endpoint on by default; request_uri valid 60 s; per-client 'PAR required' switch off by default [10, 12, 62, 63, 64] | no, no PAR endpoint in discovery metadata or URL routes (not in docs or source) [167, 201] | yes, optional by default; can be required globally or per client; rate limited by default [282, 283, 304, 305] | n/a (not an OAuth/OIDC server) [378, 379] | no (no PAR endpoint in source or discovery; open issue #10239) [445, 482] | no (no PAR endpoint in discovery or routes at the tag) [562, 594] |
| DPoP (RFC 9449) | yes, RFC 9449 supported and on: binds tokens when client sends a proof; per-client 'Require DPoP' off by default [10, 11, 12, 65, 66, 67] | partial, DPoP proofs only bind ID tokens (OIDC key binding, new in 2026.8); access tokens stay Bearer [168, 194, 202] | no (DPoP not supported; not advertised in discovery) [282, 291] | n/a (not an OAuth/OIDC server) [378, 392] | no (no DPoP in source or discovery; open issue #5402) [445, 483] | yes, DPoP-bound access and refresh tokens; server nonce enforced by default (dpop.force_nonce=true) [562, 566, 585] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| Introspection endpoint (client auth needed) | yes (Hydra): POST /admin/oauth2/introspect on admin port 4445 only; no caller authentication at all [680, 697, 698, 699, 700] | yes, /api/login/oauth/introspect; client_id + secret (Basic or POST) or private_key_jwt of a registered app [786, 794, 821, 822] | yes, caller must be a registered client using its auth method (public: own tokens only); opaque only [921, 922, 947, 948, 949] | yes, /token/introspect (since v2.40.0) for access and refresh tokens; no caller authentication required [1026, 1049, 1050, 1051, 1052] | yes, RFC 7662; no caller authentication: anyone holding a valid token can introspect it (since 1.10) [1119, 1126, 1149, 1150] | yes; client_secret_basic, a bearer access token or federated JWT assertion; only own client's tokens [1239, 1257] |
| Revocation endpoint (RFC 7009) | yes (Hydra): public POST /oauth2/revoke; requires OAuth2 client authentication [675, 680, 701] | yes, RFC 7009 /api/login/oauth/revoke (added in v4.23.0); expires the token row incl. its access token [786, 823, 824, 825] | yes, /oidc/token/revocation for opaque and refresh tokens; JWT access tokens rejected since 1.42.0 [921, 922, 949, 950] | no RFC 7009 endpoint; refresh tokens revoked only via admin gRPC RevokeRefresh or session-bound logout [1042, 1053, 1054, 1055] | yes, RFC 7009; no client authentication; revokes the whole OAuth2 session (access or refresh token) [1118, 1119, 1126, 1151] | no RFC 7009 endpoint (not in routes or discovery); users can revoke an app's grant in the UI [1239, 1245, 1246, 1258] |
| Access token format (default) | both: opaque by default; JWT via strategies.access_token or per-client access_token_strategy [702, 703, 704] | JWT only: JWT (default, full user claims), JWT-Empty, JWT-Custom, JWT-Standard; no opaque tokens [793, 826, 827, 828] | both: JWT for API resource and org tokens; opaque when no resource is requested (plain sign-in) [947, 951, 952] | JWT only: signed like ID tokens (RS256 default), no opaque option; 24h default lifetime [1056, 1057, 1058] | JWT by default (RFC 9068 at+jwt, ES256); client-credentials tokens are encrypted JWE (opaque) [1118, 1122, 1124, 1152] | JWT only (RFC 9068 profile since v2.13.0); refresh tokens and authorization codes are opaque [1240, 1241, 1259, 1260] |
| Refresh-token rotation | yes, always on: single-use refresh tokens, reuse revokes the whole chain; grace period 0s by default [705, 706, 707, 708] | yes, on by default: old refresh token revoked on use; no reuse detection or grace period; per-app opt-out [794, 799, 829] | yes, on by default: public clients rotate every use, others at 70% TTL; reuse revokes grant; no grace [953, 954, 955, 956, 957] | yes, on by default; used token rejected, no grace (reuseInterval 0), no family revocation; no default expiry [1051, 1059, 1060, 1061, 1062] | yes, always on: new refresh token on every use; reuse revokes the session; no grace period; 16 h expiry [1150, 1152, 1153, 1154] | yes, always on: old token still works for 1 min, later reuse revokes all tokens of that grant [1261, 1262, 1263] |
| RP-initiated logout | yes (Hydra): end_session_endpoint at /oauth2/sessions/logout (GET and POST) [676, 680, 709] | yes, end_session_endpoint /api/logout with id_token_hint, registered post_logout_redirect_uri, state [786, 830, 831] | yes, end_session_endpoint at /oidc/session/end [921, 922, 958] | yes, /logout since v2.46.0; off by default: needs DEX_SESSIONS_ENABLED (experimental flag) [1026, 1030, 1033, 1063, 1064] | no end_session_endpoint (issue #1997 open); only Kanidm's own /ui/logout ends the IdP session [1119, 1148, 1155, 1156, 1157] | yes, end_session_endpoint (GET/POST); id_token_hint revokes that session's tokens, then redirects [1239, 1264, 1265] |
| Back-channel logout | yes (Hydra): back-channel logout (sent asynchronously) and front-channel logout, both in discovery [675, 676, 680, 709] | yes, per-app back-channel logout URL receives logout_token (sub, sid); no front-channel logout [786, 831, 832, 833] | yes, per-app back-channel logout URI (sid optional); no front-channel logout [921, 922, 958] | yes, since v2.46.0 via per-client backchannelLogoutURI; needs experimental sessions flag; no front-channel [1026, 1033, 1065, 1066] | no back-channel or front-channel logout (not in discovery or source; tracked in issue #4240) [1155, 1158, 1159] | yes (v2.17.0+), per-client URL; sent on user disable/delete or access revoke; no sid, no front-channel [1239, 1263, 1266, 1267] |
| PAR (RFC 9126) | no: no PAR endpoint or metadata; the bundled fosite PAR handler is not wired into Hydra [676, 678, 686, 710] | no (no PAR endpoint in discovery or routes; Casdoor docs point to Keycloak for PAR) [786, 787, 834] | yes, /oidc/request advertised (oidc-provider default, not documented by Logto); optional, not required [921, 922, 959] | no (not in discovery metadata or routes; feature request #4755 open) [1042, 1053, 1067] | no PAR (no pushed authorization endpoint in routes or discovery; request_uri not supported) [1119, 1126, 1155] | yes (v2.9.0+), /api/oidc/par; optional by default, can be required per client; request_uri valid 90 s [1239, 1240, 1268, 1269] |
| DPoP (RFC 9449) | no (no DPoP code in Hydra or its fosite copy; feature request #3235 closed as stale) [676, 711] | yes, RFC 9449 DPoP on token and refresh requests, optional per request; no DPoP-Nonce or jti replay cache [786, 790, 794, 835] | no, explicitly disabled in the provider config until Logto officially supports DPoP [922, 960] | no (not in source; feature request #2872 open) [1053, 1068] | no DPoP (all tokens issued as Bearer; DPoP only appears as an IANA token-type enum value) [1124, 1152, 1160] | no; no DPoP metadata in discovery and no DPoP code in Pocket ID or its Fosite fork [1239, 1240] |

## 3. Users and admin

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| Admin web UI | yes, Admin Console (v2 UI, enabled by default) for realms, users, clients, flows and settings [28, 68, 69] | yes, Admin interface (/if/admin/) included in the open-source edition [203, 204] | no (admin dashboard is a roadmap item in the design stage) [306] | yes, built-in web UI for users, groups and attributes; users can edit own details [378, 394, 395] | yes, Management Console (Angular) at /ui/console [466, 484] | yes, built-in Admin UI at /auth/v1/admin plus a per-user account dashboard [563, 595] |
| Admin/management API | yes, Admin REST API with OAuth bearer tokens from Keycloak (realm-management roles); Admin API v2 preview [69, 70, 71, 72] | yes, REST API /api/v3/ (OpenAPI 3); Bearer API tokens, OAuth JWTs with goauthentik.io/api scope, or session [205, 206] | no admin API; admin tasks via CLI (authelia storage ...) run directly against the database [289, 306, 307] | yes, GraphQL at /api/graphql; JWT (bearer or cookie) from /auth/simple/login or OPAQUE login [384, 396, 397] | yes, gRPC, connectRPC and REST (v1 and v2 APIs); OAuth bearer tokens (key JWT, client creds, PAT) [466, 485, 486, 487] | yes, REST API under /auth/v1 (OpenAPI, Swagger UI off by default); admin session or scoped API key [596, 597] |
| Self-registration | yes, off by default (Realm settings, Login tab, User registration) [73, 74, 75] | yes, via enrollment flows; off by default: no enrollment flow shipped, only example blueprints [182, 207, 208] | no (no sign-up flow; users come from the file or LDAP backend) [282, 286, 308] | no (only admins create users; maintainer declined invite-based sign-up in #287) [395, 398, 399] | yes, on by default (AllowRegister true in the default login policy) [488, 489] | yes, off by default (user_registration.enable=false); email activation link, PoW, domain restriction [598, 599, 600] |
| Password reset by email | yes, Forgot password email link; off by default, requires SMTP settings [74, 76] | yes, via recovery flow with email stage; not set up by default (import example flow, set it on the brand) [182, 209] | yes, on by default: emailed signed link (5 min lifespan); can be disabled or replaced by custom_url [278, 309, 310, 311] | yes, emailed reset link (10-min token); off by default, needs SMTP settings [379, 381, 393, 400, 401] | yes, self-service reset via emailed code; on by default (needs an email provider); can be hidden per policy [488, 489, 490] | yes, email magic link (valid 30 min), PoW on the request; needs SMTP; not for passkey-only accounts [589, 601, 602] |
| Groups and roles | yes, realm and client roles, composite roles, hierarchical groups with inherited roles and attributes [77, 78] | yes, nested groups plus RBAC roles (permission sets) assignable to users or groups, inherited via hierarchy [210, 211] | partial: groups only (from file or LDAP backend), used in ACL rules and OIDC groups claim; no roles [286, 312, 313] | partial: flat groups; roles fixed to 3 built-in groups (admin, password manager, strict read-only) [387, 402, 403] | partial, project roles and role assignments; no user groups at this tag [463, 491, 492] | yes, custom roles and groups (roles/groups claims); delegated group admins via rauthy_admin:&lt;group&gt; [563, 603, 604] |
| Multi-tenancy | yes, many isolated realms per server; Organizations inside a realm (supported, per-realm toggle off by default) [79, 80, 81, 82, 83] | partial, per-domain brands in OSS; schema-per-tenant tenancy is (Enterprise), alpha, off by default, API-only [212, 213, 214, 215] | no (single tenant; can protect several cookie domains since 4.38; multi-issuer OIDC planned) [314, 315] | no (single base DN; FAQ suggests one instance per domain) [389] | yes, virtual instances (created via System API), each holding multiple organizations [493] | no (single namespace; delegated group admins only, docs say strict tenant isolation may come later) [603] |
| Upstream social/OIDC login | yes, OIDC, OAuth 2.0 and SAML IdP brokering plus 12 built-in social providers (Google, GitHub, Microsoft...) [27, 84, 85] | yes, OAuth/OIDC sources (generic OIDC, Apple, Entra ID, GitHub, Google, Okta...), SAML, Kerberos, Plex [216, 217] | no (upstream OIDC or social login is a roadmap item that needs design) [282, 316] | no (no upstream OIDC/social login; local password login only) [378, 379] | yes, generic OIDC, OAuth2, SAML, JWT, LDAP plus Google, GitHub, GitLab, Azure AD, Apple templates [488, 494] | yes, upstream OIDC/OAuth2 (generic, GitHub, Google templates), docs call it beta; ATProto opt-in [605, 606, 607] |
| Custom user attributes | yes, declarative User Profile schema with validators and permissions; unmanaged attributes off by default [86, 87] | yes, free-form JSON attributes on users and groups; typed object attributes added in 2026.8 (docs: Preview) [218, 219] | yes, extra attributes from file or LDAP backend plus expression-based definitions; usable in OIDC claims [317, 318] | yes, custom user and group attributes (string, integer, JPEG, date-time), since 0.6.0 [387, 404] | yes, key-value user metadata (can be added to tokens); typed user schemas are an early-stage flag [453, 495] | yes, typed custom attributes mapped to claims via custom scopes; can be made user-editable [563, 608, 609] |
| Config-as-code or Terraform provider | yes: realm JSON import (CLI or at startup), Operator CRs; Terraform provider hosted in keycloak GitHub org [72, 88, 89, 90, 91, 92] | yes, built-in YAML blueprints (config as code); official Terraform provider (goauthentik org) [220, 221] | yes, declarative YAML/env config (users file, OIDC clients, ACLs); no official Terraform provider [286, 306, 319] | yes, first-party bootstrap.sh (declarative JSON); Terraform provider is community (tasansga) [394, 405, 406] | yes, official Terraform provider (zitadel/terraform-provider-zitadel); FirstInstance YAML at setup [496, 497, 498] | partial: bootstrap JSON (clients, users, roles, groups, scopes, API keys) on first boot only; no Terraform [610, 611] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| Admin web UI | no: no admin web UI in OSS; Ory Console is Ory Network only [686, 694, 712] | yes, built-in React admin console in the open-source repo, served by the Go server [836, 837, 838] | yes, Admin Console (port 3002 by default); more Console members need a paid self-hosted license [939, 961, 962] | no (no admin UI; manage via config file or gRPC API; repo example-app has a demo API page) [1042, 1044, 1048, 1069] | partial: experimental web admin (opt-in group): browse persons, edit groups/members; all else via CLI [1161, 1162, 1163, 1164] | yes, built-in web admin UI: users, groups, OIDC clients, APIs, API keys, settings, audit log [1270, 1271] |
| Admin/management API | yes: REST admin APIs (Hydra :4445, Kratos :4434), no built-in auth, bound to 0.0.0.0 by default [699, 713, 714, 715, 716, 717] | yes, REST API with Swagger; auth by session, bearer token, client id+secret, access key, or user+password [839, 840] | yes, REST Management API at /api; bearer JWT from an M2M app via client credentials [963, 964] | yes, gRPC API, off by default; only auth is optional mTLS client certs (none = full admin access) [1048, 1062, 1070] | yes, REST /v1 and SCIM-style /scim/v1 JSON APIs with OpenAPI; bearer session or service-account API token [1143, 1165, 1166] | yes, REST /api with X-API-Key header (key has its owner's rights) or session; STATIC_API_KEY env var [1272, 1273, 1274, 1275] |
| Self-registration | yes (Kratos): self-service registration, on by default [718] | yes, per app; on in console defaults for new apps; never allowed into built-in org, so none on a fresh install [792, 793, 841, 842] | yes, on by default (OSS seed: username + password sign-up) [965, 966, 967] | no (users added only via staticPasswords config or gRPC API; no registration page) [1071, 1072] | no self-registration (persons are created by admins via CLI/API; no sign-up route in the web UI) [1148, 1167] | yes, off by default (ALLOW_USER_SIGNUPS=disabled); modes: admin signup links (withToken) or open [1251, 1271, 1275, 1276] |
| Password reset by email | yes (Kratos recovery flow): one-time code (default) or magic link by email, SMS optional; off by default [719, 720] | yes, forgot-password page sends email code or reset link (or SMS code); needs an Email/SMS provider on the app [843, 844, 845] | yes, email or SMS code; needs an email/SMS connector and enabling it, so off by default [966, 968, 969] | no (no email sending or reset flow in source; docs suggest a client app calling the gRPC API) [1048, 1072] | yes, off by default: emailed credential-reset link (account recovery); needs separate kanidm-mail-sender [1150, 1168, 1169, 1170] | n/a: no passwords (passkey-only); nearest is the optional email login code, off by default [1249, 1251, 1277, 1278] |
| Groups and roles | no: no groups or roles on identities (only traits/metadata); RBAC is Ory Keto, a separate product [721, 722] | yes, nested groups, roles (users, groups, sub-roles, domains) and Casbin-model permissions [846, 847, 848] | partial: global user/M2M roles and organization roles (RBAC); no user groups [952, 970] | partial: groups only (groups claim from connectors or local/static users); no roles concept [1043, 1073, 1074] | yes, nested groups; built-in privilege groups act as roles (RBAC); per-app OAuth2 scope/claim maps by group [1171, 1172, 1173] | partial: groups yes (groups claim, per-client allowed groups); no roles beyond a per-user admin flag [1271, 1278, 1279] |
| Multi-tenancy | no: one tenant per deployment; Kratos organizations/multi-tenancy are OEL/Ory Network only [687, 723, 724, 725, 726] | yes, organizations, each with own users, apps, providers and roles; built-in org holds the global admins [814, 849, 850, 851] | partial: organizations inside one tenant; multiple isolated tenants are Cloud only [939, 971] | no (one issuer and one storage per instance; no tenant/realm concept in source) [1075, 1076] | no, one domain per server/replication topology; separate tenants need separate deployments [1174, 1175] | no (not in docs or source); one issuer and one user base per instance [1239, 1275] |
| Upstream social/OIDC login | yes (Kratos oidc method): generic OIDC plus 24 named social providers; off by default [727, 728] | yes, about 80 OAuth/social types incl. Google, GitHub, Entra ID, generic OIDC, custom OAuth; plus SAML [803, 852, 853] | yes, social connectors (Google, GitHub, Apple...), generic OIDC/OAuth2, enterprise SSO (OIDC/SAML) [942, 943, 972] | yes, core feature: connectors for OIDC, OAuth2, GitHub, GitLab, Google, Microsoft, SAML, LDAP and more [1043, 1045] | no (upstream OAuth2 login code is early-stage, undocumented, no CLI; federation tracked in issue #4015) [1176, 1177, 1178, 1179] | no; sign-in is passkey, cross-device approval or login code only (federation is for client auth) [1277, 1280, 1281] |
| Custom user attributes | yes (Kratos): JSON Schema identity traits plus metadata_public and metadata_admin fields [721, 729] | yes, free-form Properties key-value map per user; custom JWT attributes with the JWT-Custom format [827, 854, 855] | yes, per-user custom_data JSON plus custom profile fields collected at sign-up [973, 974, 975] | no (fixed claim set: name, preferred_username, email, email_verified, groups; connectors map into it) [1073, 1077] | partial: schema extensible by schema admins via raw API, but unadvertised and undocumented (issue #3493) [1180, 1181, 1182] | yes, custom claims (key/value, JSON values allowed) on users and groups, released with profile scope [1241] |
| Config-as-code or Terraform provider | partial: YAML/env config, JSON identity schemas, CLI import; official Terraform provider is Ory Network only [730, 731, 732] | yes, init data file (JSON/YAML, can re-apply on change), official Terraform provider, first-party k8s operator [856, 857, 858, 859, 860] | no official tooling (Management API only); community Terraform provider Lenstra/logto exists [976] | yes, YAML config file (clients, connectors, users); Terraform: no official provider (community exists) [1071, 1078, 1079] | yes, built-in HJSON entry migrations (persons, groups, OAuth2 clients, 1.9+); no official Terraform provider [1131, 1183, 1184] | partial: env-var settings, STATIC_API_KEY for tools; no official Terraform provider (community ones exist) [1272, 1275, 1282] |

## 4. MFA

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| TOTP | yes, TOTP (default SHA1, 6 digits, 30 s) or HOTP; default flow asks only users who configured it [93, 94, 95] | yes, TOTP (6 or 8 digits); setup flow shipped, validated by default MFA stage once enrolled [222, 223, 224] | yes, on by default: SHA1, 6 digits, 30 s period, skew 1; code reuse blocked by default [320, 321] | no (unused totp_secret/mfa_type DB columns only; maintainer confirms not implemented) [407, 408, 409, 410] | yes, TOTP second factor, enabled by default [499, 500] | no (OTP kind 'Time' returns 'unimplemented'; docs call TOTP future work; only email OTP) [612, 613, 614] |
| WebAuthn/passkey as second factor | yes, WebAuthn authenticator as 2FA; in default browser flow but DISABLED until an admin enables it [95, 96, 97] | yes, WebAuthn/FIDO2 security keys and passkeys as second factor; setup flow shipped [224, 225, 226] | yes, on by default (WebAuthn security keys and passkeys as a second factor) [278, 322] | no (no WebAuthn/passkey code; web and LDAP login are password-only) [379, 411, 412] | yes, WebAuthn/U2F (security keys or platform authenticators) as second factor, enabled by default [499, 500] | yes, WebAuthn/FIDO2 passkeys as 2nd factor after password; user-enrolled, UV not forced by default [563, 602, 607] |
| Passwordless passkey login | yes, passkey-only login in default username forms; feature on, per-realm 'Enable Passkeys' off by default [83, 98, 99, 100, 101, 102] | yes, passwordless WebAuthn flow or passkey autofill on identification (2025.12+); not configured by default [182, 208, 227, 228] | yes, off by default (enable_passkey_login); counts as 1FA, password still asked for two_factor [322, 323] | no (password is the only login factor) [379, 382, 411] | yes, passkeys (U2F with PIN) as only factor, allowed by default [488, 499, 500, 501] | yes, passkey-only accounts (UV required); discoverable-credential 'Passkey' login button since 0.37.0 [602, 615] |
| Email or SMS OTP | no, no built-in email or SMS OTP authenticator (custom SPI needed); email only for verify/reset links [28, 103] | yes, email OTP and SMS OTP (Twilio or generic HTTP) as MFA; email magic-link login via example flow [229, 230, 231] | no; email one-time codes only verify identity (session elevation, reset); no SMS (Duo is push only) [324, 325, 326] | no (email used only for reset links and test mail; no email/SMS OTP) [379, 413] | yes, email and SMS OTP as second factor only, not enabled by default; SMS via Twilio or HTTP webhook [500, 502, 503] | yes, email OTP only (SMS unimplemented), opt-in: as 2FA, and skips password on a known device (30d) [612, 614, 616, 617, 618] |
| Recovery codes | yes, 12 one-time recovery codes (supported); form is DISABLED in the default browser flow [95, 104, 105] | yes, static one-time backup codes (default 6 codes x 12 chars); setup flow shipped [232, 233] | no (recovery codes proposed in open maintainer PR #13096, not in this release) [327] | no (no MFA; maintainer lists backup keys as future design work) [409] | partial, API only (User v2 generate, Session API check) since v4.9; neither login UI offers it [504, 505, 506, 507, 508] | no (not in source or docs); lost passkeys need an admin to reset MFA [602] |
| MFA enforcement policies | yes, via auth flows: required for all, conditional on role/attribute/client scope/LoA, per-client flow override [106, 107, 108, 109] | yes, MFA stage action skip/deny/configure plus policy bindings (group, app, conditional); default is skip [224, 227, 234, 235] | yes, ACL rules by domain, path, user, group, network, method; default_policy deny; OIDC default two_factor [312, 328, 329] | no (no MFA; maintainer suggests a Duo LDAP proxy as workaround) [408, 412] | yes, Force MFA (all or local-only users) per instance or per org; no per-group or per-app; off by default [488, 499, 509, 510, 511, 512] | partial: admin MFA (on), per-client force MFA, PAM-host and ephemeral-client MFA; no group/conditional [563, 619, 620, 621] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| TOTP | yes (Kratos totp method), off by default [733, 734] | yes, TOTP authenticator app as MFA, self-enrolled on the account page [861, 862] | yes, authenticator app TOTP factor, off by default [965, 977, 978] | yes, since v2.46.0, off by default: needs DEX_SESSIONS_ENABLED (experimental) plus mfa.authenticators [1030, 1033, 1080, 1081, 1082, 1083] | yes, TOTP (SHA-256, 6 digits, 30 s by default; SHA-1 fallback); TOTP is asked before the password [1185, 1186, 1187] | no; maintainer declined TOTP because Pocket ID is passwordless by design (#937) [1277, 1283] |
| WebAuthn/passkey as second factor | yes (Kratos webauthn method; MFA mode unless passwordless=true), off by default [734, 735, 736] | no, WebAuthn is a sign-in method only; second factors are TOTP, SMS, email, RADIUS, push [861, 862, 863] | yes, WebAuthn passkeys/security keys as MFA factor (web only), off by default [977, 979] | yes, as second factor since v2.46.0, off by default; needs experimental sessions flag plus config [1033, 1080, 1082, 1084, 1085, 1086, 1087] | partial: password + security-key 2FA deprecated (no new enrolment); WebAuthn is offered as passkeys instead [1187, 1188, 1189] | n/a: passkeys are the only sign-in factor, not a second factor (there are no passwords) [1249, 1277, 1278] |
| Passwordless passkey login | yes (Kratos passkey method, discoverable credentials and conditional UI), off by default [737, 738] | yes, WebAuthn sign-in incl. discoverable passkeys; in default sign-in methods; MFA still asked if user has it [793, 864, 865, 866] | yes, passkey sign-in since 1.38.0, off by default; separate MFA step skipped [966, 980, 981] | no (WebAuthn runs only as a second factor after connector login) [1084, 1085, 1088] | yes, passkeys are the preferred login method; attested passkeys can be required via account policy [1187, 1190, 1191] | yes, primary method: discoverable passkeys, user verification required by default [1251, 1277, 1284, 1285] |
| Email or SMS OTP | yes (Kratos code): email and SMS (HTTP gateway); passwordless or MFA mode, not both; both off by default [739, 740] | yes, email and SMS codes: as MFA and as passwordless verification-code sign-in; email magic link too [793, 861, 862, 867] | yes, email and SMS codes as MFA and as passwordless sign-in (not both on one channel); needs connectors [977, 982, 983, 984] | no (MFA types are TOTP and WebAuthn only; no email or SMS sending in source) [1072, 1080] | no email or SMS OTP (login methods: password, TOTP, backup code, security key, passkey) [1191] | partial: email only, passwordless login code (off by default, valid 15 min); admin-sent codes; no SMS [1251, 1277, 1286] |
| Recovery codes | yes (Kratos lookup_secret): 12 single-use 8-character codes, off by default [741, 742] | yes, one single-use recovery code (UUID) generated at MFA setup [862, 868, 869] | yes, 10 single-use backup codes; only alongside another MFA factor [977, 985] | no (no recovery codes; admin can reset a user's MFA via gRPC ResetMFA) [1072, 1080, 1089] | yes, 8 single-use backup codes on password+TOTP credentials; generated via CLI (not the web UI) [1192, 1193, 1194] | no; recovery is an admin-issued one-time login code (admin UI or CLI) [1287] |
| MFA enforcement policies | partial: global required_aal (default highest_available); no forced enrollment, no per-group/per-app rules [743, 744, 745] | partial, per-org (or per-user) MFA items: Optional, Prompt, Required; no per-app, group or conditional rules [870, 871] | yes: mandatory for all, per organization, adaptive risk rules; no per-app policy; off by default [977, 986, 987, 988] | partial: global defaultMFAChain or per-client mfaChain, filterable by connector type; no group/conditional [1082, 1088, 1090, 1091] | yes, per group: account-policy minimum credential (mfa/passkey/attested passkey); MFA default for persons [1190, 1195, 1196, 1197] | no MFA policies; only per-client re-authentication and global passkey rules (UV, synced, type) [1251, 1268, 1277] |

## 5. Defenses

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| Account lockout / brute-force protection | yes, per user, off by default: 30 failures, wait +1 min up to 15 min, counter reset 12 h; no per-IP lockout [75, 110, 111, 112, 113, 114, 115, 116] | partial, no lockout by default: flow cancels after 5 bad passwords; per-IP/user reputation policy unbound [182, 235, 236, 237, 238, 239, 240] | yes, per user by default (IP mode optional): 3 failed password logins in 2 min give a 5 min ban [330, 331, 332, 333, 334, 335, 336] | no: no lockout, counter or delay on LDAP bind or web/API login; only per-try Argon2id cost [382, 414, 415, 416, 417] | yes, per user, off by default (0 attempts); lock lasts until admin unlock; tarpit: +1s per 5 fails, max 10s [513, 514, 515, 516, 517, 518, 519, 520] | yes, on, per IP (per-user failures also count): 7 fails 1 min IP ban, 10: 10 min, 15: 15 min, 20: 1 h, 25+: 24 h [622, 623, 624, 625, 626, 627, 628, 629, 630, 631] |
| Rate limiting | no, no per-endpoint rate limits; only global load shedding (http-max-queued-requests, unset by default) [112, 117, 118, 119, 120] | partial, on by default but loose: anon API/flow executor 1000 req/s per IP per worker; device endpoint 20/h [171, 241, 242, 243, 244] | yes, per IP, on by default: token and PAR (failed requests only), TOTP, Duo, reset, elevation; not login, userinfo, introspect, revoke [283, 331, 335, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349] | no built-in rate limit (LDAP or HTTP); maintainer suggests fail2ban; one worker serializes binds [388, 417, 418, 419] | no built-in limiter (docs: add one at proxy/WAF); usage quotas off by default; per-IP limits (Cloud only) [521, 522, 523, 524] | partial: no general limiter; 2 parallel hashes; device-flow IP limit off; DCR 1/IP/h; PoW issuance unlimited [565, 566, 632, 633, 634, 635, 636, 637] |
| Password policy | yes: length, char classes, not username/email, regex, history, expiry, denylist file; none by default; no HIBP [121, 122, 123, 124] | yes, length, char classes, HIBP, zxcvbn; history (Enterprise); default 8 chars + zxcvbn, password change only [235, 245, 246, 247, 248] | partial: standard (min 8, max, char classes) or zxcvbn (score 3); both off by default; no HIBP, no history [350, 351, 352, 353, 354, 355] | partial: fixed 8-char min in web UI and set-password CLI only; LDAP changes unchecked; no complexity/HIBP [420, 421, 422, 423, 424, 425, 426] | yes, min length, upper/lower/number/symbol, max age; no history or breach check; default 8 + all 4 classes [525, 526, 527] | yes, length, char classes, expiry, history; default min 14, 1 lower/upper/digit, 180d expiry, last 3; no HIBP [638, 639, 640, 641] |
| CAPTCHA or proof-of-work on login | partial, registration only: Google reCAPTCHA v2/v3 or Enterprise, disabled by default; no login CAPTCHA [103, 125, 126] | yes, Captcha stage: reCAPTCHA v2/v3, hCaptcha, Turnstile, Cap (self-hosted PoW server); off by default [182, 208, 249] | no (no CAPTCHA or proof-of-work in source, web UI or docs) [278, 311] | no (no CAPTCHA or proof-of-work; login form is username + password) [379, 411] | no (not in source; captcha issue #6658 open, community captcha PR #9785 closed unmerged) [528, 529] | yes, built-in PoW (no CAPTCHA), always on: UI login, register, reset, device verify; SHA-256, difficulty 19 [600, 601, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652] |
| Default password hashing | Argon2id by default: 5 iterations, 7168 KiB, parallelism 1; configurable; PBKDF2-SHA512/256 alternatives [127, 128, 129, 130, 131, 132] | PBKDF2-SHA256 with 1,000,000 iterations (Django 5.2 default); no supported setting to change it [250, 251, 252, 253, 254] | file backend: argon2id t=3, m=64 MiB, p=4; alt scrypt, pbkdf2, sha2crypt, bcrypt; LDAP: server hashes [356, 357] | OPAQUE aPAKE (opaque-ke 0.7) with an Argon2id slow hash, m=50 MiB, t=1, p=1; hardcoded, no alternatives [384, 414, 427, 428, 429, 430] | bcrypt cost 14 by default; configurable argon2i/id, scrypt, pbkdf2, sha2-crypt; rehash on login [530, 531, 532] | Argon2id m=131072 KiB, t=4, p=8 (max 2 parallel hashes); params configurable; no other algorithms [632, 653, 654] |
| Audit/event log | yes, off by default: user and admin events saved to DB only if enabled, no expiry unless set; errors logged [75, 133, 134, 135, 136, 137, 138] | yes, on by default: logins, failures, model changes in PostgreSQL; 365-day retention; diffs (Enterprise) [235, 255, 256, 257] | partial: every 1FA/2FA attempt stored in authentication_logs table, never pruned; no admin audit log [358, 359, 360] | partial: stdout logs only: login attempts (info), failed web logins (warn); admin edits debug-only [398, 414, 415, 431] | yes, always on: append-only eventstore in PostgreSQL (logins, admin changes); kept indefinitely [533, 534, 535, 536] | partial: security events in DB, on (info+), kept 60d; no admin-action audit trail, only stdout access log [655, 656, 657, 658, 659] |
| Admin MFA enforcement | yes, via master-realm auth flows (e.g. OTP required or role condition); not required by default [95, 106, 139] | yes, via policy-bound MFA validation stage; no admin-specific switch; off by default (MFA skipped if none) [224, 227, 234, 235] | n/a (no admin accounts or admin UI); two_factor can be required for any group via ACL rules [306, 312] | no (no MFA for any account, admins included) [408, 412] | partial, no admin-only switch; set Force MFA on the login policy of the admins' org; off by default [488, 537, 538, 539] | yes, on by default: mfa.admin_force_mfa=true, admin and group-admin sessions require MFA [616, 619, 660] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| Account lockout / brute-force protection | no: no account lockout or IP throttling in OSS; only email/SMS codes capped at 5 wrong tries per flow [746, 747, 748, 749] | yes, per user, on by default: 5 failures lock 15 min (set per app); captcha replaces the lock when enabled [872, 873, 874, 875, 876, 877] | yes, per identifier, on by default: 100 failures in 1 h lock it for 60 min (temporary); no per-IP [989, 990, 991, 992] | no: no lockout or delay on failed password or TOTP attempts; blocked_until honored but never set by Dex [1092, 1093, 1094, 1095] | yes, per credential, always on: password 1-10 s lock per failure, 100+ until UTC midnight; TOTP 3 per 30 s [1198, 1199, 1200, 1201] | no lockout (no passwords); per-IP limits only: passkey login 1/5 s burst 10, login codes 1/10 s burst 5 [1288, 1289] |
| Rate limiting | no: no built-in rate limiting (Ory Network only); endpoints only carry x-ory-ratelimit-bucket tags [746, 750, 751] | partial, no general API rate limit; 1 code send per 60 s; 5 bad codes per IP lock 10 min; IP rules for Sites [875, 878, 879, 880, 881] | partial: only email/SMS send cap, 10 per recipient per 10 min, always on; no API or login rate limiter [993, 994, 995] | no built-in rate limiting; maintainers point to proxies/load balancers (issue #1970 open) [1096, 1097] | no general HTTP rate limiting; only the per-credential soft-lock delays (see D1) [1198, 1202] | yes, per IP, on by default: 100 req/s (burst 300) on API/OIDC routes, tighter on login/signup/email [1275, 1288, 1289, 1290] |
| Password policy | yes (Kratos): min 8 chars, HIBP check on (fails open), identifier-similarity check; no complexity/history [752, 753, 754, 755] | yes, default min 6 chars; options 8 chars, upper/lower/digit, special, no repeats, history, expiry; no HIBP [828, 882, 883, 884] | yes: length, 1-4 char types, HIBP, sequences, user info, words, expiry; default min 8 + HIBP; no history [996, 997, 998] | no policy: Dex accepts only admin-supplied bcrypt hashes; no length, complexity, history or breach check [1098, 1099] | yes: min 10 chars (15 if MFA not required), max 128, zxcvbn score 4, \~640-entry badlist; no history/HIBP [1203, 1204, 1205, 1206, 1207, 1208] | n/a: no end-user passwords (passkey-only), so no password policy [1249, 1278] |
| CAPTCHA or proof-of-work on login | no: CAPTCHA (Cloudflare Turnstile) is OEL/Ory Network only; OSS has UI node stubs, no config [687, 688, 756] | yes, built-in image, reCAPTCHA v2/v3, hCaptcha, Turnstile, GEETEST, Aliyun; off by default (rule None) [792, 793, 885, 886, 887] | yes, reCAPTCHA Enterprise, Turnstile, Cap (PoW, 1.44.0+) on sign-in/sign-up/reset; off by default [966, 999, 1000, 1001] | no (no CAPTCHA or proof-of-work in source or templates) [1042, 1072] | no CAPTCHA on login; built-in hash proof-of-work only on the account-recovery form (off by default) [1168, 1209, 1210] | no (not in docs or source) [1277, 1288] |
| Default password hashing | bcrypt cost 12 (Kratos; lower costs raised to 12 outside --dev); argon2id optional (128 MB, 1 iteration) [757, 758, 759, 760, 761, 762] | bcrypt cost 10 for built-in and new orgs; per-org options incl. argon2id, pbkdf2, salted SHA/MD5, plain [828, 850, 882, 888, 889, 890, 891, 892, 893, 894, 895, 896] | Argon2i t=8, m=8 MiB, p=1, fixed; imported bcrypt/MD5/SHA/Argon2id/PBKDF2 hashes rehashed on login [1002, 1003, 1004] | bcrypt only; Dex never hashes: admins supply hashes, cost 10-16 enforced (12 recommended) [1098, 1099, 1100, 1101] | Argon2id tuned at startup to \~10 ms/hash (m 8-64 MiB, t 2-16, p 1); not configurable [1211, 1212, 1213, 1214, 1215] | n/a: no end-user passwords; client secrets and API keys are stored as SHA-256 hashes [1274, 1278, 1291] |
| Audit/event log | partial: no audit store; login and HTTP request logs to stdout, OTel span events only if tracing set up [763, 764, 765, 766, 767, 768] | yes, on by default: non-GET API calls (logins, admin changes) in DB table record; kept forever by default [851, 897, 898, 899, 900, 901] | partial: sign-in/token events in Postgres logs table, on; Mgmt API changes not logged; no OSS retention [964, 1005, 1006] | partial: structured stdout logs only (logins, failed logins, some API actions); no audit store or retention [1092, 1102, 1103] | partial: auth/admin events in server log (stdout), on by default; no stored audit trail or retention setting [1216, 1217, 1218] | yes, always on, stored in the DB, 90-day default retention; sign-ins, consents, passkeys; no admin actions [1275, 1292, 1293, 1294] |
| Admin MFA enforcement | n/a: no admin accounts or admin login in the open-source edition; admin APIs have no built-in auth [699, 713] | partial, Required MFA items on built-in org cover global admins, or set per admin user; off by default [828, 870, 871, 902] | partial: admins can opt in to Console MFA; requiring it for all needs a paid self-hosted license; off [962, 1007, 1008, 1009, 1010, 1011] | n/a: no admin accounts or admin UI; gRPC admin API uses optional mTLS client certs, no MFA [1048, 1070] | yes, MFA required for all persons by default; break-glass admin/idm_admin are password-only service accounts [1195, 1219, 1220, 1221] | no admin-specific MFA; admins sign in with passkeys like all users (UV required by default) [1251, 1279, 1287] |

## 6. Operations

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| Supported databases | PostgreSQL 14-18, MariaDB, MySQL 8.0/8.4, SQL Server 2019/2022, Azure SQL, Oracle 19c/23, EDB, Aurora PG [140, 141, 142, 143] | PostgreSQL 14 to 18 only (also cache, sessions, tasks, websockets; Redis removed in 2025.10) [254, 258, 259, 260] | PostgreSQL (recommended), MySQL/MariaDB; SQLite3 for single instance only; Redis for sessions [361, 362, 363, 364, 365] | SQLite (default), PostgreSQL, MySQL/MariaDB [378, 384, 432] | PostgreSQL 14 to 18 only (CockroachDB support removed in v3.0) [540, 541, 542] | Hiqlite (embedded SQLite with Raft, default) or PostgreSQL [661, 662] |
| HA / horizontal scaling | yes, built-in clustering: embedded Infinispan, discovery via DB (jdbc-ping), sessions in DB; no extra parts [144, 145, 146, 147] | yes, stateless server and worker replicas, all state in PostgreSQL; DB HA via Postgres replication/replicas [259, 260, 261] | yes, stateless replicas with external SQL DB and Redis (standalone or Sentinel); no built-in clustering [278, 364, 365] | partial: stateless instances on a shared Postgres/MySQL with same key_seed; no built-in clustering [404, 418, 419, 430, 433, 434, 435, 436] | yes, stateless replicas sharing PostgreSQL; optional Redis cache; Login V2 runs as a separate container [540, 543, 544, 545] | yes, built-in Raft (Hiqlite) cluster, 3 or 5 nodes advised, with Hiqlite or Postgres; replicas not stateless [661, 663, 664] |
| Prometheus metrics | yes, Prometheus /metrics on management port 9000; off by default (build-time metrics-enabled) [148, 149, 150] | yes, Prometheus metrics on port 9300 (server, worker, outposts); on by default, no auth [262, 263, 264] | yes, off by default; separate listener tcp://:9959/metrics when telemetry.metrics.enabled [366, 367] | no (no metrics endpoint or metrics library in source) [380, 429] | yes, Prometheus format at /debug/metrics on the main HTTP port (8080), on by default [546, 547, 548, 549, 550, 551] | yes, Prometheus /metrics on separate port 9090, off by default (server.metrics_enable=false) [665, 666] |
| Health endpoints | yes: /health/started, /health/live, /health/ready, /health on port 9000; off by default (health-enabled) [150, 151, 152] | yes, /-/health/live/ and /-/health/ready/ (ready checks DB); outposts /outpost.goauthentik.io/ping on 9300 [262, 265, 266] | yes, GET/HEAD /api/health on the main port (9091); no separate liveness or readiness paths [368, 369] | yes, GET /health on HTTP port (static 200, no DB check) + 'lldap healthcheck' CLI; no live/ready split [380, 406, 437, 438] | yes, /debug/healthz (liveness), /debug/ready (readiness); Login V2: /ui/v2/login/healthy [549, 552, 553, 554] | yes, /auth/v1/health (DB and cache), /auth/v1/ready, /auth/v1/ping; Hiqlite :8200/ready for readiness [667, 668] |
| Official Helm chart | partial: experimental Helm chart for the Operator only (new in 26.8, OCI on quay.io); none for the server [153, 154] | yes, official chart in goauthentik/helm, published at charts.goauthentik.io [267, 268, 269] | yes, official chart (beta) at charts.authelia.com, source authelia/chartrepo [278, 370] | no (docs link third-party Evantage-WS/lldap-kubernetes; lldap/charts org repo contains no chart) [439, 440, 441] | yes, official chart in zitadel/zitadel-charts (helm repo charts.zitadel.com) [555, 556] | no (docs: no Helm chart or Kustomize files yet; raw StatefulSet manifests in the book) [664] |
| Stated minimum/recommended resources | yes, HA sizing guide: \~1250 MB RAM base per pod; 1 vCPU per 15 password logins/s; 150% CPU headroom [155, 156] | yes, Docker Compose: host with at least 2 CPU cores and 2 GB RAM; no Kubernetes sizing stated [267, 270, 271] | partial: no general CPU/RAM sizing; K8s FAQ says allow 1GB RAM for argon2id with the file backend [371] | partial: no minimum/recommended spec; FAQ says &lt;10 MB RAM incl. DB, \~15 MiB at startup; no CPU figure [378, 389] | yes: \~512 MB RAM and under 1 CPU core (4 cores advised for hashing); minimal HA: 3 nodes x 4 CPU/16 GB [557] | partial: k8s example requests 64Mi RAM, 100m CPU; RAM must also fit m_cost/1024 x hash threads Mi (256Mi) [661, 669] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| Supported databases | PostgreSQL, MySQL 8+, CockroachDB; SQLite supported but not for production [769, 770, 771] | MySQL/MariaDB/TiDB, PostgreSQL/CockroachDB, SQL Server, SQLite; Oracle in docs but no driver at tag [903, 904] | PostgreSQL only (14 or newer) [961, 1012] | PostgreSQL, MySQL 5.7+, etcd v3, Kubernetes CRDs; SQLite3 not for real workloads; memory for dev [1104, 1105] | embedded SQLite only; external databases are not supported [1222] | SQLite (default, built in) and PostgreSQL [1275, 1295] |
| HA / horizontal scaling | yes: stateless replicas sharing one SQL DB; Kratos courier must run as a singleton; multi-region is OEL [699, 723, 772] | yes, replicas on a shared DB with Redis for sessions and device codes; CAS tickets need sticky sessions [796, 838, 859, 905, 906, 907] | yes, stateless replicas sharing PostgreSQL; optional Redis 6 central cache; no built-in clustering [1013, 1014, 1015, 1016] | yes, stateless replicas on shared storage (Postgres, MySQL, etcd, K8s CRDs); no clustering or extra parts [1076, 1105, 1106] | partial: built-in multi-master replication (mTLS), no extra components; supported topology max 2 nodes [1222, 1223, 1224, 1225] | no: one instance per database (cluster capped at 1 replica); HA work tracked in open issue #1549 [1275, 1296, 1297, 1298] |
| Prometheus metrics | yes, on by default on admin ports: Hydra :4445/admin/metrics/prometheus, Kratos :4434/metrics/prometheus [773, 774, 775] | yes, /api/metrics on the main HTTP port 8000; on by default, needs global-admin session or Prometheus key [908, 909, 910] | no, only optional Azure Application Insights telemetry (connection-string env var), off by default [1017] | yes, /metrics on separate telemetry listener; off unless telemetry.http set (Helm chart sets :5558) [1107, 1108, 1109, 1110, 1111] | no Prometheus endpoint (not in source); OpenTelemetry OTLP gRPC export only, off by default [1225, 1226, 1227] | yes, off by default: OTEL_METRICS_EXPORTER=prometheus serves /metrics on localhost:9464 [1275, 1299] |
| Health endpoints | yes: /health/alive (process up) and /health/ready (checks DB) on public and admin ports of both [774, 775, 776] | yes, GET /api/health (no auth, no DB query), used for liveness, readiness and startup probes [909, 911, 912] | partial: GET /api/status returns 204, unauthenticated; no separate liveness/readiness checks [1018, 1019] | yes: issuer-path /healthz on main port; telemetry port /healthz, /healthz/live, /healthz/ready [1107, 1111, 1112] | partial: GET /status returns true/false; no separate liveness or readiness paths [1226, 1228, 1229, 1230] | yes, GET /healthz returns 204 (no separate liveness/readiness); 'pocket-id healthcheck' CLI calls it [1300, 1301] |
| Official Helm chart | yes: official charts in ory/k8s (hydra and kratos chart 0.64.0, appVersion v26.2.0) [777, 778, 779, 780] | yes, official chart in main repo (manifests/casdoor), published as OCI on ghcr.io; first-party operator too [859, 913, 914, 915] | no (no official chart; a community Helm PR was closed unmerged; docs show a raw K8s Deployment) [1015, 1020] | yes, official dexidp/helm-charts repo (chart 0.26.0 ships app 2.46.0, not yet 2.46.1) [1079, 1113] | no official Helm chart (none in repo or docs; Kubernetes support issue #282 open) [1231] | no; docs list only community Helm charts and a community operator [1302, 1303] |
| Stated minimum/recommended resources | no: not stated; no CPU/RAM minimums in deployment, scalability or production docs [699, 769, 770, 772] | partial, at least 100 MB RAM to run a prebuilt image, 2 GB to build it; no CPU figure stated [916, 917] | yes, docs: minimum recommended 2 vCPU, 8 GiB RAM, 256 GiB disk [1012] | no, not stated in docs; Helm chart sets no requests/limits (commented example 100m CPU, 128Mi) [1046, 1105, 1114] | partial: x86_64_v2 or aarch64 CPU; about 64 KB RAM and up to 8 KB disk per entry; no core/RAM minimum [1232] | no, not stated (docs only say 'low resource usage'; no CPU/RAM figures) [1301, 1302, 1304] |

## 7. License and governance

| Feature | Keycloak 26.8.1 | authentik 2026.8.5 | Authelia 4.39.28 | LLDAP 0.6.3 | Zitadel v4.20.0 | Rauthy 0.37.2 |
|---|---|---|---|---|---|---|
| License (SPDX) | Apache-2.0; exception: vendored libpam4j files under federation/sssd are MIT [157, 158, 159, 160] | MIT; authentik/enterprise/ under proprietary authentik EE license; website/ CC-BY-SA-4.0 [204, 272, 273] | Apache-2.0; web/src/components/UI is MIT, one file BSD-3-Clause, test fonts OFL-1.1 [372, 373] | GPL-3.0-only for the whole repo (all crates inherit; single LICENSE) [442, 443] | AGPL-3.0-only; Apache-2.0 for proto/ and apps/docs/; MIT for apps/login/ and packages/zitadel-\* [558, 559] | Apache-2.0 for the whole repo incl. rauthy-client; PAM/NSS modules are a separate repo (GPLv3 deps) [573, 670, 671, 672] |
| Open-core split | no paid edition; Red Hat build of Keycloak sells support/LTS of Keycloak versions; no OSS feature gating found [143, 161, 162, 163] | yes, Enterprise adds GWS/Entra sync, WS-Fed, SSF, PAM, mTLS, EAP-TLS, password history, tenants, audit diffs [212, 274] | no paid edition (community project with no monetization model) [374, 375] | no paid edition (volunteer project; no commercial support offered) [389] | no feature-gated paid edition; paid: Zitadel Cloud hosting, Enterprise license (support/SLA, commercial terms) [558, 560] | no paid edition (single open-source edition; maintainer offers paid support) [673, 674] |
| Main backer or maintainer | IBM: 8 of 11 listed maintainers incl. project lead; also Bosch, Hitachi, Identity Tailor; CNCF incubating [92, 164, 165] | Authentik Security Inc.; creator and top committer Jens Langhammer [204, 272, 275] | Volunteer team, no company: core Clement Michaud, James Elliott, Amir Zarrinkafsh; 2 maintainers [374, 376, 377] | Individual maintainer Valentin Tolmer (@nitnelave); volunteers; FAQ says bus factor 1 [389, 442] | Company-backed: ZITADEL (CAOS Ltd./CAOS AG), St. Gallen, Switzerland [561] | No backing company: individual maintainer Sebastian Dobe (sebadob); NLnet NGI Zero Core funded [671, 673] |

| Feature | Ory Hydra + Kratos v26.2.0 | Casdoor v4.24.0 | Logto v1.45.0 | Dex v2.46.1 | Kanidm 1.11.2 | Pocket ID v2.19.1 |
|---|---|---|---|---|---|---|
| License (SPDX) | Apache-2.0 for both repos; bundled oryx/reqlog directory is MIT [781, 782, 783] | Apache-2.0 (single LICENSE at repo root, no other license files in the tag) [918] | MPL-2.0 for all packages; one vendored test helper (jest-koa-mocks) is MIT [1021, 1022, 1023] | Apache-2.0 (single LICENSE at repo root; no directories under other licenses found) [1115, 1116] | MPL-2.0 for the project; tools/orca/names-dataset (benchmark test data) is MIT [1233, 1234, 1235] | BSD-2-Clause (single root LICENSE; no subdirectories under other licenses found) [1305] |
| Open-core split | yes: OEL/Network add SCIM, SAML, B2B orgs, CAPTCHA, multi-tenancy, ROPC, zero-downtime upgrades, CVE builds [687, 712, 723, 726, 750, 766, 784] | no paid edition; Casdoor Cloud hosts the same OSS build (adds hosting, custom domain, regions, support) [838, 919] | yes: Cloud only multi-tenant, Protected App, IdP-init SSO; paid license: Console MFA/members, BYO UI, &gt;3 SAML [937, 938, 939, 962, 1011, 1024] | no paid edition (single open-source edition) [1044, 1116] | no paid edition (single MPL-2.0 codebase; no commercial or hosted edition in docs) [1233, 1236, 1237] | no paid edition; single BSD-2-Clause codebase supported by sponsorships [1305, 1306] |
| Main backer or maintainer | Ory Corp; Hydra MAINTAINERS lists Aeneas Rekkas and Patrik Neu [781, 785] | Casbin Inc. (operates Casdoor Cloud); lead maintainer Yang Luo (hsluoyz) [919, 920] | Silverhand Inc., the company behind Logto and Logto Cloud [1014, 1022] | CNCF Sandbox project; maintainers Maksim Nabokikh (Palark GmbH) and Mark Sagi-Kazar [1044, 1117] | No backing company stated; led by William Brown (Firstyear) and James Hodgkinson (yaleman) [1234, 1238] | No company: individual maintainers Elias Schneider (stonith404, creator) and Kyle Mendell (kmendell) [1305, 1306] |

## Sources

### Keycloak 26.8.1

1. Docs at tag: Specifications implemented, OpenID: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/specifications.adoc#L20-L39>
2. Keycloak guide: Specifications implemented (published): <https://www.keycloak.org/securing-apps/specifications>
3. OIDC discovery metadata: issuer and endpoints: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/OIDCWellKnownProvider.java#L119-L129>
4. Docs at tag: OpenID Connect: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-oidc.adoc#L1-L12>
5. Docs at tag: Client credentials grant: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-oidc-auth-flows.adoc#L68-L73>
6. Docs at tag: OIDC client settings, Service account roles: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/oidc/con-basic-settings.adoc#L70>
7. Docs at tag: Using a service account: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/oidc/proc-using-a-service-account.adoc#L3-L16>
8. Admin console source: new client default values: <https://github.com/keycloak/keycloak/blob/26.8.1/js/apps/admin-ui/src/clients/add/NewClientForm.tsx#L62-L74>
9. Registered OAuth2 grant type factories: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/resources/META-INF/services/org.keycloak.protocol.oidc.grants.OAuth2GrantTypeFactory#L1-L10>
10. Docs at tag: Specifications implemented, OAuth: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/specifications.adoc#L41-L65>
11. Profile.java: DPOP and DEVICE_FLOW Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L127-L129>
12. Profile.java: feature Type definitions (DEFAULT = supported, enabled by default): <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L314-L346>
13. Device grant gated by DEVICE_FLOW feature: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/grants/device/DeviceGrantTypeFactory.java#L55-L56>
14. Per-client device grant switch: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi/src/main/java/org/keycloak/models/OAuth2DeviceConfig.java#L113-L115>
15. Docs at tag: Device authorization grant: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-oidc-auth-flows.adoc#L96-L102>
16. Docs at tag: Token exchange overview (standard V2 vs legacy V1): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/token-exchange.adoc#L10-L24>
17. Docs at tag: How to enable standard token exchange: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/token-exchange.adoc#L96-L99>
18. Docs at tag: Token exchange comparison table and delegation (preview): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/token-exchange.adoc#L313-L344>
19. Profile.java: token exchange V1 (preview), standard V2 (default), delegation (preview): <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L92-L94>
20. 26.8.0 release notes: Token exchange delegation (preview): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#token-exchange-delegation-with-consent-fgap-authorization-and-audit-trail-preview>
21. 26.2.0 release notes: Supported Standard Token Exchange: <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#supported-standard-token-exchange>
22. Keycloak guide: Configuring and using token exchange: <https://www.keycloak.org/securing-apps/token-exchange>
23. Docs at tag: Creating a SAML client: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/saml/proc-creating-saml-client.adoc#L1-L6>
24. Docs at tag: SAML bindings and endpoint: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-saml-bindings.adoc#L1-L42>
25. Docs at tag: Specifications implemented, SAML: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/specifications.adoc#L80-L86>
26. Docs at tag: SAML: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-saml.adoc#L1-L13>
27. Built-in identity provider types (OIDC, OAuth2, SAML, ...): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/resources/META-INF/services/org.keycloak.broker.provider.IdentityProviderFactory>
28. Docs at tag: Server Administration Guide feature list: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/overview/features.adoc#L4-L28>
29. Docs at tag: LDAP and Active Directory federation: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/user-federation/ldap.adoc#L3-L38>
30. Docs at tag: SCIM introduction: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/scim/intro.adoc#L11-L25>
31. Docs at tag: Enabling SCIM for a realm: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/scim/enabling-scim.adoc#L4-L38>
32. Per-realm SCIM flag defaults to false: <https://github.com/keycloak/keycloak/blob/26.8.1/model/jpa/src/main/java/org/keycloak/models/jpa/RealmAdapter.java#L1381-L1382>
33. SCIM resources served only when realm SCIM is enabled: <https://github.com/keycloak/keycloak/blob/26.8.1/scim/services/src/main/java/org/keycloak/scim/services/ScimRealmResourceFactory.java#L38>
34. Profile.java: SCIM_API Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L206>
35. Keycloak 26.8.0 release notes: SCIM API (supported): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#scim-api-supported>
36. Upgrading guide 26.8.0: SCIM API is now enabled by default: <https://www.keycloak.org/docs/26.8.1/upgrading/index.html#scim-api-is-now-enabled-by-default>
37. Docs at tag: SCIM supported and unsupported capabilities: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/scim/accessing-service-config.adoc#L56-L70>
38. Docs at tag: SCIM endpoint authorization (bearer token): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/scim/accessing-endpoints.adoc#L7-L12>
39. Docs at tag: Workflow built-in steps: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/workflows/defining-steps.adoc#L56-L113>
40. Keycloak 26.8.1 Server Administration Guide: Managing users and groups through SCIM: <https://www.keycloak.org/docs/26.8.1/server_admin/index.html#_managing_scim>
41. Docs at tag: Specifications implemented, SCIM (listed as Tech Preview): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/specifications.adoc#L110-L117>
42. Docs at tag: recommended client-side implementations: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/partials/overview/getting-started.adoc#L7-L51>
43. Docs at tag: mod_auth_openidc (no official support): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/mod-auth-openidc.adoc#L10-L15>
44. Introspection endpoint client authorization: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenIntrospectionEndpoint.java#L161-L178>
45. Docs at tag: Token introspection audience validation: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/oidc/con-audience.adoc#L200-L208>
46. Discovery: token and introspection endpoint auth methods: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/OIDCWellKnownProvider.java#L158-L164>
47. Revocation endpoint: refresh vs access token handling: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenRevocationEndpoint.java#L90-L139>
48. Revocation endpoint: client auth and issued-for check: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenRevocationEndpoint.java#L186-L246>
49. Revocation endpoint: access token revoked-token store: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenRevocationEndpoint.java#L278-L283>
50. Docs at tag: Server OIDC URI endpoints: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-server-oidc-uri-endpoints.adoc#L12-L39>
51. Access token encoded as signed JWT: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java#L1492-L1493>
52. Default signature algorithm RS256: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/models/Constants.java#L68>
53. Docs at tag: Using lightweight access token: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/con-protocol-mappers.adoc#L81-L86>
54. Docs at tag: Refresh token rotation: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-oidc-auth-flows.adoc#L85-L94>
55. New refresh token generated on each refresh: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/refresh/AbstractRefreshTokenProvider.java#L169-L172>
56. Refresh token reuse handling (detach client session): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/refresh/AbstractRefreshTokenProvider.java#L282-L303>
57. Realm creation defaults: revokeRefreshToken false, max reuse 0: <https://github.com/keycloak/keycloak/blob/26.8.1/model/storage-private/src/main/java/org/keycloak/storage/datastore/DefaultExportImportManager.java#L249-L253>
58. Admin console help text: Revoke Refresh Token: <https://github.com/keycloak/keycloak/blob/26.8.1/js/apps/admin-ui/maven-resources/theme/keycloak.v2/admin/messages/messages_en.properties#L2599>
59. TokenManager.validateTokenReuse: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/TokenManager.java#L325-L355>
60. Docs at tag: OIDC logout (RP-initiated, front-channel, back-channel): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/sso-protocols/con-oidc-auth-flows.adoc#L312-L381>
61. Docs at tag: OIDC client logout settings: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/oidc/con-basic-settings.adoc#L116-L131>
62. OIDC discovery: DPoP, revocation, back-channel logout, PAR: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/OIDCWellKnownProvider.java#L202-L223>
63. Profile.java: PAR Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L104>
64. PAR config: request_uri lifespan and per-client requirement: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi/src/main/java/org/keycloak/models/ParConfig.java#L30-L85>
65. Docs at tag: Configuring DPoP: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/dpop.adoc#L149-L158>
66. Per-client DPoP requirement flag: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/OIDCAdvancedConfigWrapper.java#L184-L187>
67. 26.4.0 release notes: DPoP (supported): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#dpop-supported>
68. Docs at tag: Using the Admin Console: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/realms/proc-using-admin-console.adoc#L1-L16>
69. Profile.java: ADMIN_API, CLIENT_ADMIN_API_V2 (preview), ADMIN_V2: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L72-L76>
70. Docs at tag: Admin REST API: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_development/topics/admin-rest-api.adoc#L1-L35>
71. Docs at tag: Admin API v2 (preview): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/admin-api/admin-api-v2.adoc#L6-L15>
72. 26.8.0 release notes: Admin API v2 and Operator client CRs (preview): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#declarative-client-management-with-admin-api-v2-preview>
73. Docs at tag: Enabling user registration: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/users/proc-enabling-user-registration.adoc#L6-L16>
74. RealmEntity: registrationAllowed and resetPasswordAllowed fields: <https://github.com/keycloak/keycloak/blob/26.8.1/model/jpa/src/main/java/org/keycloak/models/jpa/entities/RealmEntity.java#L73-L79>
75. RealmManager.setupRealmDefaults (brute force, event listener): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/managers/RealmManager.java#L269-L299>
76. Docs at tag: Enabling forgot password: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/login-settings/forgot-password.adoc#L3-L23>
77. Docs at tag: Assigning permissions using roles and groups: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/assembly-roles-groups.adoc#L1-L7>
78. Docs at tag: Groups: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/roles-groups/proc-managing-groups.adoc#L1-L14>
79. Docs at tag: Configuring realms: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/realms.adoc#L1-L9>
80. Docs at tag: Organizations introduction: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/organizations/intro.adoc#L1-L23>
81. Docs at tag: Enabling organizations: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/organizations/managing-organization.adoc#L3-L18>
82. Per-realm organizations flag defaults to false: <https://github.com/keycloak/keycloak/blob/26.8.1/model/jpa/src/main/java/org/keycloak/models/jpa/RealmAdapter.java#L1339-L1340>
83. Profile.java: ORGANIZATION and PASSKEYS Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L160-L162>
84. Docs at tag: Integrating identity providers: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/identity-broker.adoc#L1-L14>
85. Built-in social identity providers: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/resources/META-INF/services/org.keycloak.broker.social.SocialIdentityProviderFactory>
86. Docs at tag: Managing user attributes (user profile): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/users/user-profile.adoc#L1-L25>
87. Docs at tag: Unmanaged attributes policy: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/users/user-profile.adoc#L89-L100>
88. Docs at tag: Importing and exporting realms: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/importExport.adoc#L110-L156>
89. Docs at tag: Operator realm import: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/operator/realm-import.adoc#L10-L20>
90. Terraform provider keycloak/keycloak README (keycloak GitHub org): <https://github.com/keycloak/terraform-provider-keycloak/blob/v5.10.0/README.md>
91. Terraform provider maintainers: <https://github.com/keycloak/terraform-provider-keycloak/blob/v5.10.0/MAINTAINERS.md>
92. Keycloak governance: project list: <https://github.com/keycloak/keycloak/blob/26.8.1/GOVERNANCE.md#L19-L29>
93. Docs at tag: OTP policies: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/otp-policies.adoc#L1-L27>
94. Default OTP policy: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi/src/main/java/org/keycloak/models/OTPPolicy.java#L75>
95. Default browser flow definition: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/models/utils/DefaultAuthenticationFlows.java#L344-L425>
96. Docs at tag: WebAuthn setup for 2FA: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/webauthn.adoc#L17-L60>
97. Profile.java: WEB_AUTHN Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L98>
98. Docs at tag: Passkeys: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/passkeys.adoc#L5-L23>
99. Docs at tag: Passkeys setup (Enable Passkeys switch): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/passkeys.adoc#L90-L100>
100. Passkeys enabled check (feature and realm switch): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/authentication/authenticators/browser/WebAuthnConditionalUIAuthenticator.java#L65-L68>
101. WebAuthn policy default: passkeysEnabled null: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/models/WebAuthnPolicyTwoFactorDefaults.java#L49>
102. 26.4.0 release notes: Passkeys integration (supported): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#passkeys-integration-supported>
103. Shipped authenticator factories: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/resources/META-INF/services/org.keycloak.authentication.AuthenticatorFactory>
104. Docs at tag: Recovery codes: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/recovery-codes.adoc#L1-L40>
105. Profile.java: RECOVERY_CODES Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L121>
106. Docs at tag: Conditions in conditional flows: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/conditions.adoc#L1-L76>
107. Docs at tag: 2FA conditional workflow examples: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/conditions.adoc#L120-L156>
108. Per-client authentication flow override resolution: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/models/utils/AuthenticationFlowResolver.java#L36-L90>
109. Docs at tag: auth-flow-enforce client policy executor: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/clients/client-policies.adoc#L164>
110. Keycloak 26.8.1 Server Administration Guide: Brute force attacks: <https://www.keycloak.org/docs/26.8.1/server_admin/index.html#password-guess-brute-force-attacks>
111. Docs at tag: Brute force detection and default parameters: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/threat/brute-force.adoc#L1-L115>
112. Docs at tag: Downside of brute force detection (use IPS for IP blocking): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/threat/brute-force.adoc#L284-L288>
113. Brute force login failures keyed by user: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/managers/DefaultBruteForceProtector.java#L80-L105>
114. 26.8.0 release notes: Login failures now stored in the database: <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#login-failures-now-stored-in-the-database>
115. Profile.java: login failures v1/v2, multi-site, stateless, clusterless: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L133-L140>
116. Admin console source: brute force mode presets: <https://github.com/keycloak/keycloak/blob/26.8.1/js/apps/admin-ui/src/realm-settings/security-defences/BruteForceDetection.tsx#L96-L117>
117. Docs at tag: Limit the number of queued requests: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/configuration-production.adoc#L44-L53>
118. http-max-queued-requests option: <https://github.com/keycloak/keycloak/blob/26.8.1/quarkus/config-api/src/main/java/org/keycloak/config/HttpOptions.java#L132-L136>
119. Docs at tag: Limit authentication sessions (firewall ingress limits): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/threat/auth-sessions-limit.adoc#L14-L15>
120. Docs at tag: SSF verification rate limit (experimental feature): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/securing-apps/ssf-support.adoc#L284-L288>
121. Docs at tag: Password policies (none at realm creation): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/password-policies.adoc#L1-L24>
122. Docs at tag: Password policy types: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/password-policies.adoc#L25-L177>
123. Registered password policy providers: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/resources/META-INF/services/org.keycloak.policy.PasswordPolicyProviderFactory#L18-L35>
124. Keycloak 26.8.1 Server Administration Guide: Password policies: <https://www.keycloak.org/docs/26.8.1/server_admin/index.html#_password-policies>
125. Docs at tag: Enabling reCAPTCHA: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/users/proc-enabling-recaptcha.adoc#L5-L40>
126. Default registration flow: reCAPTCHA execution DISABLED: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/models/utils/DefaultAuthenticationFlows.java#L126-L141>
127. Docs at tag: Hashing algorithms and default iterations: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/authentication/password-policies.adoc#L27-L92>
128. Argon2 default parameters: <https://github.com/keycloak/keycloak/blob/26.8.1/crypto/default/src/main/java/org/keycloak/crypto/hash/Argon2Parameters.java#L9-L14>
129. Argon2 provider factory reads defaults (configurable): <https://github.com/keycloak/keycloak/blob/26.8.1/crypto/default/src/main/java/org/keycloak/crypto/hash/Argon2PasswordHashProviderFactory.java#L56-L62>
130. Argon2 provider order 300: <https://github.com/keycloak/keycloak/blob/26.8.1/crypto/default/src/main/java/org/keycloak/crypto/hash/Argon2PasswordHashProviderFactory.java#L155-L158>
131. Default provider selection: highest order: <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/DefaultKeycloakSessionFactory.java#L262-L275>
132. PBKDF2-SHA512 iterations and order: <https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/credential/hash/Pbkdf2Sha512PasswordHashProviderFactory.java#L19-L34>
133. Docs at tag: Auditing user events: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/events/login.adoc#L1-L20>
134. Docs at tag: Logging event listener: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/events/login.adoc#L150-L190>
135. Docs at tag: Auditing admin events: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/events/admin.adoc#L1-L26>
136. Logging event listener levels (success debug, error warn): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/events/log/JBossLoggingEventListenerProviderFactory.java#L56-L57>
137. Expired user events purged only if expiration &gt; 0: <https://github.com/keycloak/keycloak/blob/26.8.1/model/jpa/src/main/java/org/keycloak/events/jpa/JpaEventStoreProvider.java#L90-L97>
138. RealmEntity event settings fields: <https://github.com/keycloak/keycloak/blob/26.8.1/model/jpa/src/main/java/org/keycloak/models/jpa/entities/RealmEntity.java#L170-L188>
139. Admin console client setup (public OIDC client): <https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/managers/RealmManager.java#L192-L213>
140. Docs at tag: Configuring the database, supported databases: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/db.adoc#L12-L21>
141. Docs at tag: supported databases table: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/templates/databases.adoc#L4-L18>
142. Profile.java: DB_TIDB experimental: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L179>
143. Docs at tag: database drivers (product vs community differences): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/db.adoc#L23-L43>
144. Docs at tag: Configuring distributed caches (jdbc-ping): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/caching.adoc#L10-L23>
145. Docs at tag: User session caching (sessions in DB): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/server/caching.adoc#L104-L118>
146. Profile.java: PERSISTENT_USER_SESSIONS Type.DEFAULT: <https://github.com/keycloak/keycloak/blob/26.8.1/common/src/main/java/org/keycloak/common/Profile.java#L146>
147. 26.8.0 release notes: Multi-cluster v2 (supported): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#multi-cluster-v2-supported>
148. Docs at tag: Metrics: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/observability/configuration-metrics.adoc#L13-L25>
149. metrics-enabled option default false: <https://github.com/keycloak/keycloak/blob/26.8.1/quarkus/config-api/src/main/java/org/keycloak/config/MetricsOptions.java#L5-L10>
150. Management interface port default 9000: <https://github.com/keycloak/keycloak/blob/26.8.1/quarkus/config-api/src/main/java/org/keycloak/config/ManagementOptions.java#L60-L64>
151. Docs at tag: Health checks: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/observability/health.adoc#L11-L24>
152. health-enabled option default false: <https://github.com/keycloak/keycloak/blob/26.8.1/quarkus/config-api/src/main/java/org/keycloak/config/HealthOptions.java#L5-L10>
153. Docs at tag: Installing the Operator by using Helm (experimental): <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/operator/installation.adoc#L262-L290>
154. 26.8.0 release notes: Helm Chart Operator install (experimental): <https://www.keycloak.org/docs/26.8.1/release_notes/index.html#helm-chart-operator-install-experimental>
155. Docs at tag: CPU and memory sizing recommendations: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/guides/high-availability/partials/concepts/perf_recommendations.adoc#L12-L39>
156. Keycloak guide: Concepts for sizing CPU and memory resources: <https://www.keycloak.org/high-availability/single-cluster/concepts-memory-and-cpu-sizing>
157. LICENSE.txt (Apache License 2.0): <https://github.com/keycloak/keycloak/blob/26.8.1/LICENSE.txt>
158. Docs at tag: License: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/License.adoc#L9-L10>
159. Vendored libpam4j source with MIT License header: <https://github.com/keycloak/keycloak/blob/26.8.1/federation/sssd/src/main/java/org/jvnet/libpam/PAM.java#L1-L22>
160. pom.xml licenses block (Apache License 2.0): <https://github.com/keycloak/keycloak/blob/26.8.1/pom.xml#L271-L277>
161. SECURITY.md: Red Hat build of Keycloak for long term support: <https://github.com/keycloak/keycloak/blob/26.8.1/SECURITY.md#L42-L48>
162. Docs attributes: community vs product build flags: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/topics/templates/document-attributes.adoc#L1-L4>
163. Keycloak guide: Enabling and disabling features (latest = 26.8.1): <https://www.keycloak.org/server/features>
164. Keycloak active maintainers: <https://github.com/keycloak/keycloak/blob/26.8.1/MAINTAINERS.md#L1-L13>
165. Keycloak is a CNCF incubating project: <https://github.com/keycloak/keycloak/blob/26.8.1/docs/cncf.md#L1-L3>

### authentik 2026.8.5

166. authentik 2026.8 docs: OAuth 2.0 provider: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/>
167. authentik source @2026.8.5: OIDC discovery metadata (providers/oauth2/views/provider.py): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/provider.py#L56-L128>
168. authentik release notes 2026.8: <https://version-2026-8.goauthentik.io/releases/2026.8/>
169. authentik 2026.8 docs: Machine-to-machine authentication: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/machine_to_machine/>
170. authentik 2026.8 docs: Device code flow: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/device_code/>
171. authentik source @2026.8.5: device authorization endpoint throttle: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/device_backchannel.py#L79-L84>
172. authentik 2026.8 docs: Token exchange: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/token_exchange/>
173. authentik source @2026.8.5: OAuth2 provider form default grant types: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/web/src/admin/providers/oauth2/OAuth2ProviderFormForm.ts#L136-L156>
174. authentik source @2026.8.5: OAuth2Provider.grant_types default: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/models.py#L232>
175. authentik source @2026.8.5: Enterprise Agent serializer (EnterpriseRequiredMixin): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/enterprise/agents/api.py#L34-L37>
176. authentik 2026.8 docs: Agent accounts (Enterprise): <https://version-2026-8.goauthentik.io/users-sources/user/account-types/agent-accounts/>
177. authentik 2026.8 docs: SAML Provider: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/saml/>
178. authentik source @2026.8.5: SAML provider URL routes: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/saml/urls.py#L14-L60>
179. authentik 2026.8 docs: LDAP Provider: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/ldap/>
180. authentik 2026.8 docs: Outposts: <https://version-2026-8.goauthentik.io/add-secure-apps/outposts/>
181. authentik 2026.8 docs: LDAP source: <https://version-2026-8.goauthentik.io/users-sources/sources/protocols/ldap/>
182. authentik source @2026.8.5: default authentication flow blueprint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/default/flow-default-authentication-flow.yaml#L19-L69>
183. authentik 2026.8 docs: SCIM source: <https://version-2026-8.goauthentik.io/users-sources/sources/protocols/scim/>
184. authentik 2026.8 docs: SCIM Provider: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/scim/>
185. authentik 2026.8 docs: RADIUS Provider: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/radius/>
186. authentik source @2026.8.5: EAP-TLS Enterprise license check: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/enterprise/providers/radius/api.py#L9-L14>
187. authentik 2026.8 docs: Forward auth: <https://version-2026-8.goauthentik.io/add-secure-apps/providers/proxy/forward_auth/>
188. authentik source @2026.8.5: proxy outpost forward-auth routes: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/src/outpost/proxy/application/mod.rs#L142-L163>
189. authentik 2026.8 docs: Embedded Outpost: <https://version-2026-8.goauthentik.io/add-secure-apps/outposts/embedded/>
190. authentik source @2026.8.5: token introspection view: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/introspection.py#L41-L64>
191. authentik source @2026.8.5: client authentication (Basic or POST): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/utils.py#L110-L135>
192. authentik source @2026.8.5: token revocation view: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/token_revoke.py#L30-L60>
193. authentik source @2026.8.5: AccessToken (JWT) and RefreshToken (opaque) models: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/models.py#L631-L682>
194. authentik source @2026.8.5: to_access_token (JWT encoding, cnf stripped): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/id_token.py#L167-L175>
195. authentik source @2026.8.5: refresh token validity and threshold defaults: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/models.py#L288-L305>
196. authentik source @2026.8.5: refresh token rotation: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/token.py#L216-L245>
197. authentik source @2026.8.5: revoked refresh token reuse handling: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/token/refresh_token.py#L39-L47>
198. authentik source @2026.8.5: OIDC RP-initiated logout endpoint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/views/end_session.py#L40-L111>
199. authentik 2026.8 docs: Front-channel and back-channel logout (Preview badge): <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/frontchannel_and_backchannel_logout/>
200. authentik source @2026.8.5: OAuth2 provider logout URI and method default: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/models.py#L249-L262>
201. authentik source @2026.8.5: OAuth2 provider URL routes: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/providers/oauth2/urls.py#L25-L69>
202. authentik 2026.8 docs: OpenID Connect key binding (DPoP proofs): <https://version-2026-8.goauthentik.io/add-secure-apps/providers/oauth2/key-binding/>
203. authentik source @2026.8.5: Admin interface route: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/core/urls.py#L50-L51>
204. authentik LICENSE @2026.8.5: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/LICENSE>
205. authentik API docs @2026.8.5: Authentication: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/website/api/authentication.mdx>
206. authentik source @2026.8.5: REST API authentication classes: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/root/settings.py#L249-L252>
207. authentik source @2026.8.5: example enrollment blueprint (instantiate false): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/example/flows-enrollment-2-stage.yaml#L1-L5>
208. authentik source @2026.8.5: identification stage defaults (captcha, webauthn, enrollment, recovery): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/stages/identification/models.py#L36-L128>
209. authentik 2026.8 docs: User basic operations, credentials recovery: <https://version-2026-8.goauthentik.io/users-sources/user/user_basic_operations/>
210. authentik 2026.8 docs: Roles: <https://version-2026-8.goauthentik.io/users-sources/roles/>
211. authentik 2026.8 docs: Groups: <https://version-2026-8.goauthentik.io/users-sources/groups/>
212. authentik 2026.8 docs: Tenancy (Enterprise, alpha): <https://version-2026-8.goauthentik.io/sys-mgmt/tenancy/>
213. authentik source @2026.8.5: tenants API enterprise check: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/tenants/api/tenants.py#L93-L97>
214. authentik source @2026.8.5: default config tenants.enabled false: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/lib/default.yml#L156-L158>
215. authentik 2026.8 docs: Branding (brands): <https://version-2026-8.goauthentik.io/customize/branding/>
216. authentik 2026.8 docs: Federated and social sources: <https://version-2026-8.goauthentik.io/users-sources/sources/>
217. authentik source @2026.8.5: built-in OAuth source types: <https://github.com/goauthentik/authentik/tree/version/2026.8.5/authentik/sources/oauth/types>
218. authentik 2026.8 docs: User properties and attributes: <https://version-2026-8.goauthentik.io/users-sources/user/user_ref/>
219. authentik 2026.8 docs: Object attributes (Preview): <https://version-2026-8.goauthentik.io/sys-mgmt/object-attributes/>
220. authentik 2026.8 docs: Blueprints: <https://version-2026-8.goauthentik.io/customize/blueprints/>
221. goauthentik/terraform-provider-authentik (project-maintained Terraform provider): <https://github.com/goauthentik/terraform-provider-authentik>
222. authentik 2026.8 docs: TOTP authenticator setup stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_totp/>
223. authentik source @2026.8.5: default TOTP setup flow blueprint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/default/flow-default-authenticator-totp-setup.yaml#L14-L21>
224. authentik source @2026.8.5: authenticator validation stage defaults: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/stages/authenticator_validate/models.py#L33-L68>
225. authentik 2026.8 docs: WebAuthn / FIDO2 / Passkeys setup stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_webauthn/>
226. authentik source @2026.8.5: default WebAuthn setup flow blueprint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/default/flow-default-authenticator-webauthn-setup.yaml>
227. authentik 2026.8 docs: Authenticator validation stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_validate/>
228. authentik 2026.8 docs: Identification stage (passkey autofill): <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/identification/>
229. authentik 2026.8 docs: Email authenticator setup stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_email/>
230. authentik 2026.8 docs: SMS authenticator setup stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_sms/>
231. authentik source @2026.8.5: example email magic-link login blueprint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/example/flows-login-email-magic-link.yaml#L1-L35>
232. authentik 2026.8 docs: Static authenticator setup stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/authenticator_static/>
233. authentik source @2026.8.5: static token count/length defaults: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/stages/authenticator_static/models.py#L21-L22>
234. authentik 2026.8 docs: Policy, group, and user bindings: <https://version-2026-8.goauthentik.io/customize/policies/bindings/>
235. authentik 2026.8 docs: Hardening authentik: <https://version-2026-8.goauthentik.io/security/security-hardening/>
236. authentik source @2026.8.5: password stage failed_attempts_before_cancel: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/stages/password/models.py#L48-L54>
237. authentik 2026.8 docs: Password stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/password/>
238. authentik source @2026.8.5: reputation score updates: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/policies/reputation/signals.py#L23-L67>
239. authentik source @2026.8.5: reputation policy defaults and expiry: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/policies/reputation/models.py#L23-L33>
240. authentik source @2026.8.5: default reputation limits: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/tenants/models.py#L32-L35>
241. authentik source @2026.8.5: default throttle config: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/lib/default.yml#L115-L119>
242. authentik source @2026.8.5: DRF throttle class and per-worker cache: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/root/settings.py#L261-L282>
243. authentik source @2026.8.5: flow executor DRF APIView: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/flows/views/executor.py#L100-L104>
244. authentik source @2026.8.5: OTP exponential back-off: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/stages/authenticator/models.py#L339-L357>
245. authentik source @2026.8.5: default password policy blueprint: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/blueprints/default/flow-password-change.yaml#L5-L15>
246. authentik source @2026.8.5: password policy model defaults: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/policies/password/models.py#L31-L51>
247. authentik 2026.8 docs: Password Policy: <https://version-2026-8.goauthentik.io/customize/policies/types/password/>
248. authentik 2026.8 docs: Password uniqueness policy (Enterprise): <https://version-2026-8.goauthentik.io/customize/policies/types/password-uniqueness/>
249. authentik 2026.8 docs: Captcha stage: <https://version-2026-8.goauthentik.io/add-secure-apps/flows-stages/stages/captcha/>
250. Django 5.2.17 source: PBKDF2PasswordHasher iterations: <https://github.com/django/django/blob/5.2.17/django/contrib/auth/hashers.py#L311-L322>
251. Django 5.2.17 source: default PASSWORD_HASHERS: <https://github.com/django/django/blob/5.2.17/django/conf/global_settings.py#L544-L550>
252. authentik source @2026.8.5: Django version pin: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/pyproject.toml#L29>
253. authentik 2026.8 docs: Automated install (password hash example): <https://version-2026-8.goauthentik.io/install-config/automated-install/>
254. authentik 2026.8 docs: Configuration (PostgreSQL, custom Python settings): <https://version-2026-8.goauthentik.io/install-config/configuration/>
255. authentik 2026.8 docs: Events: <https://version-2026-8.goauthentik.io/sys-mgmt/events/>
256. authentik 2026.8 docs: Logging events: <https://version-2026-8.goauthentik.io/sys-mgmt/events/logging-events/>
257. authentik source @2026.8.5: event retention and GDPR defaults: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/tenants/models.py#L89-L117>
258. authentik release notes 2025.10 (Redis removal): <https://version-2026-8.goauthentik.io/releases/2025.10/>
259. authentik source @2026.8.5: PostgreSQL-backed cache and sessions: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/root/settings.py#L268-L284>
260. authentik source @2026.8.5: PostgreSQL channel layer (websockets): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/root/settings.py#L364-L372>
261. authentik 2026.8 docs: High availability: <https://version-2026-8.goauthentik.io/install-config/high-availability/>
262. authentik 2026.8 docs: Monitoring: <https://version-2026-8.goauthentik.io/sys-mgmt/ops/monitoring/>
263. authentik source @2026.8.5: default listen addresses: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/lib/default.yml#L36-L48>
264. authentik source @2026.8.5: metrics server: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/src/metrics/mod.rs#L70-L92>
265. authentik source @2026.8.5: server health routes: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/src/server/core.rs#L276-L284>
266. authentik source @2026.8.5: root URLs (health, metrics hooks): <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/root/urls.py#L47-L52>
267. authentik 2026.8 docs: Kubernetes installation: <https://version-2026-8.goauthentik.io/install-config/install/kubernetes/>
268. goauthentik/helm (project Helm chart repository): <https://github.com/goauthentik/helm>
269. authentik README @2026.8.5: Helm chart repository link: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/README.md#L24>
270. authentik 2026.8 docs: Docker Compose installation: <https://version-2026-8.goauthentik.io/install-config/install/docker-compose/>
271. authentik 2026.8 docs: AWS CloudFormation installation: <https://version-2026-8.goauthentik.io/install-config/install/aws/>
272. authentik Enterprise Edition license @2026.8.5: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/authentik/enterprise/LICENSE>
273. authentik website/ LICENSE (CC BY-SA 4.0) @2026.8.5: <https://github.com/goauthentik/authentik/blob/version/2026.8.5/website/LICENSE>
274. authentik 2026.8 docs: Enterprise features: <https://version-2026-8.goauthentik.io/enterprise/enterprise-features/>
275. GitHub organization goauthentik (Authentik Security): <https://github.com/goauthentik>

### Authelia 4.39.28

276. Authelia docs@v4.39.28: OIDC integration guide, OpenID Certified: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/openid-connect/introduction.md#L35-L38>
277. Authelia docs@v4.39.28: OIDC provider roadmap, beta status and not enabled by default: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/openid-connect-1.0-provider.md#L25-L29>
278. Authelia README@v4.39.28: features summary: <https://github.com/authelia/authelia/blob/v4.39.28/README.md#L72-L105>
279. Authelia source: discovery grant_types_supported: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/discovery.go#L29-L35>
280. Authelia docs@v4.39.28: OIDC integration guide, Grant Types table: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/openid-connect/introduction.md#L324-L341>
281. Authelia docs@v4.39.28: OIDC roadmap Beta 6 (v4.38.0) and Beta 7 (v4.39.0): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/openid-connect-1.0-provider.md#L133-L187>
282. Authelia docs@v4.39.28: OIDC integration guide, Support Chart: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/openid-connect/introduction.md#L572-L630>
283. Authelia source: OIDC route registration and rate limiters: <https://github.com/authelia/authelia/blob/v4.39.28/internal/server/handlers.go#L392-L526>
284. Authelia docs@v4.39.28: OIDC roadmap, OAuth 2.0 Token Exchange (no status): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/openid-connect-1.0-provider.md#L275-L279>
285. Authelia docs@v4.39.28: SAML 2.0 Provider roadmap (planning): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/planning/security-assertion-markup-language-saml-2.0-identity-provider.md#L23-L33>
286. Authelia docs@v4.39.28: authentication backends (LDAP, file): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/first-factor/introduction.md#L25-L28>
287. Authelia go.mod: go-ldap client library: <https://github.com/authelia/authelia/blob/v4.39.28/go.mod#L23>
288. Authelia docs@v4.39.28: LDAP integration, binding and implementations: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/ldap/introduction.md#L24-L77>
289. Authelia source: OpenAPI spec of the HTTP API: <https://github.com/authelia/authelia/blob/v4.39.28/api/openapi.yml>
290. Authelia docs@v4.39.28: Proxy Authorization, default authz endpoints: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/reference/guides/proxy-authorization.md#L38-L46>
291. Authelia source: discovery endpoint auth methods: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/discovery.go#L89-L116>
292. authelia/oauth2-provider v0.3.2 (used by Authelia 4.39.28): introspection caller authentication: <https://github.com/authelia/oauth2-provider/blob/v0.3.2/introspection_request_handler.go#L183-L235>
293. authelia/oauth2-provider v0.3.2: introspection endpoint AllowMethodNone false: <https://github.com/authelia/oauth2-provider/blob/v0.3.2/client_authentication.go#L381-L385>
294. Authelia docs@v4.39.28: client introspection_endpoint_auth_method: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-providers/openid-connect/clients.md#L1146-L1156>
295. Authelia source: introspection client auth never disabled: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/config.go#L1092-L1096>
296. Authelia docs@v4.39.28: client access_token_signed_response_alg: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-providers/openid-connect/clients.md#L706-L728>
297. Authelia source: DefaultOpenIDConnectClientConfiguration: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/identity_providers.go#L272-L287>
298. Authelia source: opaque access tokens, authelia_at\_ prefix with HMAC: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/util.go#L420>
299. authelia/oauth2-provider v0.3.2: refresh grant, inactive token triggers reuse handling: <https://github.com/authelia/oauth2-provider/blob/v0.3.2/handler/oauth2/flow_refresh.go#L54-L68>
300. authelia/oauth2-provider v0.3.2: refresh token rotation and reuse revocation: <https://github.com/authelia/oauth2-provider/blob/v0.3.2/handler/oauth2/flow_refresh.go#L205-L280>
301. Authelia source: Store.RotateRefreshToken: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/store.go#L254-L275>
302. Authelia docs@v4.39.28: OIDC roadmap Beta 9 (logout specs, not started): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/openid-connect-1.0-provider.md#L230-L245>
303. Authelia source: Back-Channel Logout not implemented: <https://github.com/authelia/authelia/blob/v4.39.28/internal/oidc/config.go#L1123-L1127>
304. Authelia docs@v4.39.28: provider require_pushed_authorization_requests: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-providers/openid-connect/provider.md#L387-L391>
305. Authelia docs@v4.39.28: client require_pushed_authorization_requests: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-providers/openid-connect/clients.md#L432-L434>
306. Authelia docs@v4.39.28: roadmap, Dashboard / Control Panel and CLI for Admins: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/dashboard-control-panel-and-cli-for-admins.md#L23-L103>
307. Authelia docs@v4.39.28: CLI authelia storage user: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/reference/cli/authelia/authelia_storage_user.md>
308. Authelia issue #8949, maintainer comment on user registration: <https://github.com/authelia/authelia/issues/8949#issuecomment-2727024762>
309. Authelia docs@v4.39.28: password_reset and password_change options: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/first-factor/introduction.md#L65-L86>
310. Authelia docs@v4.39.28: Reset Password identity validation: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-validation/reset-password.md#L21-L57>
311. Authelia source: portal 1FA, reset password and elevation routes: <https://github.com/authelia/authelia/blob/v4.39.28/internal/server/handlers.go#L256-L292>
312. Authelia docs@v4.39.28: access control rule subjects: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/security/access-control.md#L247-L265>
313. Authelia docs@v4.39.28: users database example with groups: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/reference/guides/passwords.md#L30-L50>
314. Authelia docs@v4.39.28: roadmap, Multi-Domain Protection: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/multi-domain-protection.md#L23-L69>
315. Authelia docs@v4.39.28: OIDC roadmap, Multi-Issuer Configuration: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/active/openid-connect-1.0-provider.md#L257-L267>
316. Authelia docs@v4.39.28: roadmap, OpenID Connect 1.0 Relying Party: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/roadmap/planning/openid-connect-1.0-relying-party.md#L22-L46>
317. Authelia docs@v4.39.28: file backend extra_attributes: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/first-factor/file.md#L117-L135>
318. Authelia docs@v4.39.28: LDAP attributes.extra: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/first-factor/ldap.md#L482-L495>
319. GitHub: authelia organization repositories: <https://github.com/orgs/authelia/repositories>
320. Authelia source: TOTP schema and DefaultTOTPConfiguration: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/totp.go#L9-L37>
321. Authelia docs@v4.39.28: TOTP disable_reuse_security_policy: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/second-factor/time-based-one-time-password.md#L173-L179>
322. Authelia source: WebAuthn schema flags: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/webauthn.go#L17-L20>
323. Authelia docs@v4.39.28: WebAuthn enable_passkey_login: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/second-factor/webauthn.md#L69-L92>
324. Authelia docs@v4.39.28: Elevated Session identity validation: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-validation/elevated-session.md#L21-L28>
325. Authelia source: Duo methods, PossibleMethods push only: <https://github.com/authelia/authelia/blob/v4.39.28/internal/duo/const.go#L8-L20>
326. Authelia source: valid default 2FA methods: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/validator/const.go#L566>
327. Authelia PR #13096 (open): feat: add two-factor recovery codes: <https://github.com/authelia/authelia/pull/13096>
328. Authelia docs@v4.39.28: access control default_policy: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/security/access-control.md#L75-L84>
329. Authelia docs@v4.39.28: client authorization_policy default: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/identity-providers/openid-connect/clients.md#L330-L332>
330. Authelia source: Regulation schema and defaults: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/regulation.go#L11-L25>
331. Authelia source: koanf defaults map (max_retries, rate limit enable): <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/defaults.go#L7-L24>
332. Authelia source: Regulator, enablement and 1FA-only ban checks: <https://github.com/authelia/authelia/blob/v4.39.28/internal/regulation/regulator.go#L19-L66>
333. Authelia source: Regulator ban expiry calculation: <https://github.com/authelia/authelia/blob/v4.39.28/internal/regulation/regulator.go#L186-L214>
334. Authelia docs@v4.39.28: Regulation configuration: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/security/regulation.md#L23-L77>
335. Authelia source: defaults map loaded as first config source: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/sources.go#L381-L398>
336. Authelia v4.39.16 release notes: configuration max retries default (#11173): <https://github.com/authelia/authelia/releases/tag/v4.39.16>
337. Authelia source: ServerEndpointRateLimits schema: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/server.go#L62-L88>
338. Authelia source: DefaultServerConfiguration rate limit buckets: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/server.go#L152-L238>
339. Authelia source: validator fills default rate limit buckets: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/validator/server.go#L284-L340>
340. Authelia source: RateLimiter.Middleware passthrough without buckets: <https://github.com/authelia/authelia/blob/v4.39.28/internal/middlewares/rate_limiting.go#L76-L86>
341. Authelia source: WithRateLimitConfig: <https://github.com/authelia/authelia/blob/v4.39.28/internal/middlewares/rate_limiting.go#L178-L194>
342. Authelia source: per-IP token bucket construction: <https://github.com/authelia/authelia/blob/v4.39.28/internal/middlewares/rate_limiting.go#L288-L296>
343. Authelia source: portal routes and their rate limiters: <https://github.com/authelia/authelia/blob/v4.39.28/internal/server/handlers.go#L256-L361>
344. Authelia docs@v4.39.28: Server Endpoint Rate Limits: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/miscellaneous/server-endpoint-rate-limits.md#L26-L151>
345. Authelia source: RequestCtxRemoteIP uses X-Forwarded-For: <https://github.com/authelia/authelia/blob/v4.39.28/internal/middlewares/wrap.go#L37-L49>
346. Authelia docs@v4.39.28: proxy integration, Remote IP from X-Forwarded-For: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/proxies/introduction.md#L68-L71>
347. Authelia v4.39.0 release notes: tokenized bucket rate limit (#8321), ip bans (#7230): <https://github.com/authelia/authelia/releases/tag/v4.39.0>
348. Authelia v4.39.17 release notes: oidc configurable rate limits (#11696): <https://github.com/authelia/authelia/releases/tag/v4.39.17>
349. Authelia v4.39.20 release notes: middlewares add rate limit exclusions (#12159): <https://github.com/authelia/authelia/releases/tag/v4.39.20>
350. Authelia source: PasswordPolicy schema and defaults: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/password_policy.go#L7-L39>
351. Authelia source: password policy providers: <https://github.com/authelia/authelia/blob/v4.39.28/internal/middlewares/password_policy.go#L20-L97>
352. Authelia docs@v4.39.28: Password Policy: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/security/password-policy.md#L23-L124>
353. Authelia source: reset password applies password policy: <https://github.com/authelia/authelia/blob/v4.39.28/internal/handlers/handler_reset_password.go#L172>
354. Authelia source: change password applies password policy: <https://github.com/authelia/authelia/blob/v4.39.28/internal/handlers/handler_change_password.go#L56>
355. Authelia published JSON schema v4.39: password_policy.standard.max_length: <https://github.com/authelia/authelia/blob/v4.39.28/docs/static/schemas/v4.39/json-schema/configuration.json#L3192-L3197>
356. Authelia source: DefaultPasswordConfig (hashing): <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/authentication.go#L210-L242>
357. Authelia docs@v4.39.28: file backend password hashing options: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/first-factor/file.md#L166-L206>
358. Authelia source: every attempt appended to authentication log: <https://github.com/authelia/authelia/blob/v4.39.28/internal/regulation/regulator.go#L39-L54>
359. Authelia source: SQL statements on authentication_logs: <https://github.com/authelia/authelia/blob/v4.39.28/internal/storage/sql_provider.go#L69-L71>
360. Authelia docs@v4.39.28: privacy policy, security event logging: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/policies/privacy.md#L50-L57>
361. Authelia docs@v4.39.28: Database Integrations: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/reference/integrations/database-integrations.md#L21-L22>
362. Authelia docs@v4.39.28: MySQL storage (MySQL and MariaDB): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/storage/mysql.md#L8>
363. Authelia docs@v4.39.28: SQLite storage caveats: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/storage/sqlite.md#L22-L29>
364. Authelia docs@v4.39.28: Statelessness / HA considerations: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/overview/authorization/statelessness.md#L24-L79>
365. Authelia docs@v4.39.28: Cache Integrations (Redis): <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/reference/integrations/cache-integrations.md#L21>
366. Authelia source: telemetry metrics schema and defaults: <https://github.com/authelia/authelia/blob/v4.39.28/internal/configuration/schema/telemetry.go#L17-L40>
367. Authelia docs@v4.39.28: telemetry metrics: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/telemetry/metrics.md#L40-L51>
368. Authelia source: /api/health routes: <https://github.com/authelia/authelia/blob/v4.39.28/internal/server/handlers.go#L218-L219>
369. Authelia source: OpenAPI /api/health: <https://github.com/authelia/authelia/blob/v4.39.28/api/openapi.yml#L102-L124>
370. Authelia docs@v4.39.28: Kubernetes Helm Chart: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/kubernetes/chart.md#L21-L53>
371. Authelia docs@v4.39.28: Kubernetes FAQ, RAM usage: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/kubernetes/introduction.md#L63-L70>
372. Authelia LICENSE at v4.39.28 (Apache License 2.0): <https://github.com/authelia/authelia/blob/v4.39.28/LICENSE>
373. Authelia REUSE.toml at v4.39.28: <https://github.com/authelia/authelia/blob/v4.39.28/REUSE.toml#L8-L60>
374. Authelia docs@v4.39.28: About: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/information/about.md#L26-L28>
375. Authelia docs@v4.39.28: Financial contributions: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/contributing/prologue/financial.md#L23-L25>
376. Authelia docs data@v4.39.28: team profiles: <https://github.com/authelia/authelia/blob/v4.39.28/docs/data/profiles.json>
377. Authelia docs@v4.39.28: Governance, teams: <https://github.com/authelia/authelia/blob/v4.39.28/docs/content/policies/governance.md#L43-L54>

### LLDAP 0.6.3

378. LLDAP README (v0.6.3): About: LDAP-only auth server, OAuth/OpenID via other components, DB backends: <https://github.com/lldap/lldap/blob/v0.6.3/README.md#L47-L82>
379. LLDAP auth_service.rs: complete /auth route list: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/auth_service.rs#L626-L666>
380. LLDAP server/src/tcp_server.rs: HTTP route table: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/tcp_server.rs#L115-L168>
381. LLDAP server/src/configuration.rs (v0.6.3): configuration defaults: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/configuration.rs#L35-L158>
382. LLDAP crates/ldap/src/password.rs: LDAP bind handling: <https://github.com/lldap/lldap/blob/v0.6.3/crates/ldap/src/password.rs#L18-L63>
383. LLDAP crates/ldap/src/handler.rs: supported LDAP operations: <https://github.com/lldap/lldap/blob/v0.6.3/crates/ldap/src/handler.rs#L298-L334>
384. LLDAP docs/architecture.md (v0.6.3): LDAP subset, HTTP APIs, storage, OPAQUE + Argon2, JWTs, logout blacklist: <https://github.com/lldap/lldap/blob/v0.6.3/docs/architecture.md#L1-L87>
385. LLDAP migration tool manifest: CLI migration tool from OpenLDAP: <https://github.com/lldap/lldap/blob/v0.6.3/migration-tool/Cargo.toml#L1-L6>
386. LLDAP server/Cargo.toml: ldap3 client is only a dev-dependency: <https://github.com/lldap/lldap/blob/v0.6.3/server/Cargo.toml#L140-L143>
387. LLDAP GraphQL schema (v0.6.3): <https://github.com/lldap/lldap/blob/v0.6.3/schema.graphql#L1-L217>
388. LLDAP server/src/main.rs: builds LDAP and HTTP servers, server.workers(1): <https://github.com/lldap/lldap/blob/v0.6.3/server/src/main.rs#L203-L237>
389. LLDAP docs/faq.md (v0.6.3): resource use, vhosts/multi-tenancy, commercial support, maintainer, sustainability: <https://github.com/lldap/lldap/blob/v0.6.3/docs/faq.md#L63-L116>
390. LLDAP README (v0.6.3): Recommended architecture (reverse proxy + Authelia/Authentik/KeyCloak in front): <https://github.com/lldap/lldap/blob/v0.6.3/README.md#L111-L135>
391. LLDAP auth_service.rs: logout and in-memory JWT blacklist: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/auth_service.rs#L282-L321>
392. LLDAP server/src/auth_service.rs: JWT creation (HS512, 1 day) and refresh: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/auth_service.rs#L51-L138>
393. LLDAP server/src/sql_tcp_backend_handler.rs: refresh token 30 days, reset token 10 minutes: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/sql_tcp_backend_handler.rs#L43-L153>
394. LLDAP README (v0.6.3): Usage: web UI, custom attributes, bootstrap.sh, unofficial Terraform provider, GraphQL: <https://github.com/lldap/lldap/blob/v0.6.3/README.md#L90-L109>
395. LLDAP web UI routes (no sign-up page): <https://github.com/lldap/lldap/blob/v0.6.3/app/src/components/router.rs#L3-L35>
396. LLDAP docs/scripting.md (v0.6.3): LDAP scope, GraphQL API, getting a JWT: <https://github.com/lldap/lldap/blob/v0.6.3/docs/scripting.md#L1-L99>
397. LLDAP server/src/graphql_server.rs: GraphQL endpoint and JWT bearer check: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/graphql_server.rs#L122-L167>
398. LLDAP GraphQL create_user mutation: admin only, debug-level span: <https://github.com/lldap/lldap/blob/v0.6.3/crates/graphql-server/src/mutation/mod.rs#L50-L60>
399. lldap#287, maintainer: self-registration via invite not worth the extra complexity: <https://github.com/lldap/lldap/issues/287#issuecomment-1476878554>
400. LLDAP auth_service.rs: password reset step 1: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/auth_service.rs#L152-L209>
401. LLDAP Docker config template (v0.6.3): key_file/key_seed and SMTP password-reset options: <https://github.com/lldap/lldap/blob/v0.6.3/lldap_config.docker_template.toml#L104-L133>
402. LLDAP README (v0.6.3): built-in groups lldap_admin, lldap_password_manager, lldap_strict_readonly; no password-hash export: <https://github.com/lldap/lldap/blob/v0.6.3/README.md#L154-L193>
403. LLDAP crates/access-control: permissions derived from the 3 built-in groups: <https://github.com/lldap/lldap/blob/v0.6.3/crates/access-control/src/lib.rs#L240-L262>
404. LLDAP CHANGELOG: 0.6.2 to 0.5.0 entries (custom attributes, JWT secret required, 3 s reset sleep, key seed for multiple containers): <https://github.com/lldap/lldap/blob/v0.6.3/CHANGELOG.md#L57-L248>
405. LLDAP bootstrap.sh docs: declarative JSON provisioning: <https://github.com/lldap/lldap/blob/v0.6.3/example_configs/bootstrap/bootstrap.md#L1-L42>
406. LLDAP Dockerfile: copies config template and bootstrap.sh, ports, HEALTHCHECK: <https://github.com/lldap/lldap/blob/v0.6.3/Dockerfile#L76-L98>
407. LLDAP sql_migrations.rs: users table incl. unused totp_secret/mfa_type columns: <https://github.com/lldap/lldap/blob/v0.6.3/crates/sql-backend-handler/src/sql_migrations.rs#L160-L175>
408. lldap#631, maintainer: TOTP is not currently supported: <https://github.com/lldap/lldap/issues/631#issuecomment-1662269527>
409. lldap#631, maintainer: DB allowances for TOTP exist but it is not implemented; backup keys still to design: <https://github.com/lldap/lldap/issues/631#issuecomment-2344636576>
410. lldap PR #1484 (open, opened 2026-08-11): optional TOTP two-factor authentication, not in 0.6.3: <https://github.com/lldap/lldap/pull/1484>
411. LLDAP web UI login form: username and password only: <https://github.com/lldap/lldap/blob/v0.6.3/app/src/components/login.rs#L25-L32>
412. lldap#631, maintainer: a Duo LDAP proxy is the recommended MFA workaround: <https://github.com/lldap/lldap/issues/631#issuecomment-1831435061>
413. LLDAP server/src/mail.rs: password reset and test emails, 3 s sleep on send failure: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/mail.rs#L82-L131>
414. LLDAP sql_opaque_handler.rs: passwords_match and bind (LDAP bind and simple login): <https://github.com/lldap/lldap/blob/v0.6.3/crates/sql-backend-handler/src/sql_opaque_handler.rs#L18-L95>
415. LLDAP sql_opaque_handler.rs: OPAQUE login and registration handlers: <https://github.com/lldap/lldap/blob/v0.6.3/crates/sql-backend-handler/src/sql_opaque_handler.rs#L97-L211>
416. LLDAP auth_service.rs: /auth/simple/login calls the same bind as LDAP: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/auth_service.rs#L427-L442>
417. lldap#1026, maintainer: set a rate limiter like fail2ban in front of the endpoint: <https://github.com/lldap/lldap/issues/1026#issuecomment-2456741677>
418. LLDAP server/src/tcp_server.rs: HTTP server setup, JWT blacklist loaded once at startup, middleware: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/tcp_server.rs#L201-L265>
419. lldap#1474, maintainer (on 0.6.3): binds expensive by design, serialized \~250 ms, scale with more instances on a shared DB: <https://github.com/lldap/lldap/issues/1474#issuecomment-5112184434>
420. LLDAP web UI change-password form: min length 8: <https://github.com/lldap/lldap/blob/v0.6.3/app/src/components/change_password.rs#L34-L54>
421. LLDAP web UI create-user form: password empty or at least 8: <https://github.com/lldap/lldap/blob/v0.6.3/app/src/components/create_user.rs#L70-L89>
422. LLDAP web UI reset-password form: min length 8: <https://github.com/lldap/lldap/blob/v0.6.3/app/src/components/reset_password_step2.rs#L23-L28>
423. LLDAP lldap_set_password CLI: min 8 unless --bypass-password-policy: <https://github.com/lldap/lldap/blob/v0.6.3/set-password/src/main.rs#L103-L114>
424. LLDAP crates/ldap/src/modify.rs: userPassword change over LDAP: <https://github.com/lldap/lldap/blob/v0.6.3/crates/ldap/src/modify.rs#L15-L62>
425. LLDAP server/src/main.rs: initial admin password required, minimum 8 characters: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/main.rs#L46-L60>
426. LLDAP CHANGELOG: 0.6.3 entry: <https://github.com/lldap/lldap/blob/v0.6.3/CHANGELOG.md#L8-L55>
427. LLDAP crates/auth/src/opaque.rs: Argon2id parameters and OPAQUE cipher suite: <https://github.com/lldap/lldap/blob/v0.6.3/crates/auth/src/opaque.rs#L16-L60>
428. opaque-ke v0.7.0 (version pinned in LLDAP Cargo.lock): slow hash applied to the OPRF output in the client finish steps: <https://github.com/facebook/opaque-ke/blob/v0.7.0/src/opaque.rs#L906-L912>
429. LLDAP Cargo.lock (v0.6.3): opaque-ke 0.7.0: <https://github.com/lldap/lldap/blob/v0.6.3/Cargo.lock#L3269-L3272>
430. LLDAP configuration.rs: server key derived from key_seed (ChaCha20 seeded by SHA-256) or key file: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/configuration.rs#L365-L410>
431. LLDAP server/src/logging.rs: default log filter (info), output to stdout: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/logging.rs#L38-L54>
432. LLDAP CI: runs LLDAP against PostgreSQL, MariaDB and SQLite: <https://github.com/lldap/lldap/blob/v0.6.3/.github/workflows/docker-build-static.yml#L50-L252>
433. lldap#126, maintainer: LLDAP is made to be stateless so several instances can run in parallel: <https://github.com/lldap/lldap/issues/126#issuecomment-2619569409>
434. lldap#881, maintainer: set LLDAP_KEY_SEED to a random value shared between instances: <https://github.com/lldap/lldap/issues/881#issuecomment-2024042001>
435. LLDAP configuration.rs: private-key error message about several instances sharing the key: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/configuration.rs#L238-L250>
436. lldap#1467, maintainer: multiple instances are not the primary use case (startup migration race): <https://github.com/lldap/lldap/issues/1467#issuecomment-5014743772>
437. LLDAP server/src/healthcheck.rs: HTTP check of /health: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/healthcheck.rs#L188-L195>
438. LLDAP server/src/main.rs: healthcheck subcommand: <https://github.com/lldap/lldap/blob/v0.6.3/server/src/main.rs#L249-L287>
439. LLDAP docs/install.md (v0.6.3): Docker configuration, default-config note, Kubernetes pointer: <https://github.com/lldap/lldap/blob/v0.6.3/docs/install.md#L14-L103>
440. lldap/charts repository (no chart files on main or gh-pages; last push 2024-04-04): <https://github.com/lldap/charts>
441. lldap#881, maintainer created lldap/charts for a community Helm chart: <https://github.com/lldap/lldap/issues/881#issuecomment-2035650481>
442. LLDAP workspace Cargo.toml: authors, license GPL-3.0-only: <https://github.com/lldap/lldap/blob/v0.6.3/Cargo.toml#L12-L19>
443. LLDAP LICENSE (GNU GPL v3 text): <https://github.com/lldap/lldap/blob/v0.6.3/LICENSE>

### Zitadel v4.20.0

444. Zitadel docs (v4.20.0 source): OpenID Connect endpoints, discovery: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/endpoints.mdx?plain=1#L11-L30>
445. Zitadel v4.20.0 source: OIDC discovery metadata (createDiscoveryConfig): <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/server.go#L178-L223>
446. Zitadel docs (v4.20.0 source): supported grant types: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/grant-types.mdx?plain=1#L9-L20>
447. Zitadel docs (v4.20.0 source): client credentials for service accounts: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/service-accounts/client-credentials.mdx?plain=1#L7-L25>
448. Zitadel v4.20.0 source: client_credentials grant routed to service-account auth: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/client.go#L184-L193>
449. Zitadel v4.20.0 source: clientCredentialsAuth (machine user secret): <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/client_credentials.go#L17-L40>
450. Zitadel v4.20.0 defaults.yaml: device authorization endpoint and lifetimes: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L684-L696>
451. Zitadel docs (v4.20.0 source): Token Exchange guide, token types and actor token: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/token-exchange.mdx?plain=1#L11-L102>
452. Zitadel docs (v4.20.0 source): impersonation security setting and roles: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/token-exchange.mdx?plain=1#L446-L461>
453. Zitadel v4.20.0 proto: user_schema flag (early stage), deprecated oidc_token_exchange flag: <https://github.com/zitadel/zitadel/blob/v4.20.0/proto/zitadel/feature/v2/instance.proto#L24-L39>
454. Zitadel v4.20.0 source: token exchange verification and impersonation check: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/token_exchange.go#L55-L175>
455. Zitadel v4.11.0 release notes: move token exchange from beta to GA (#11475): <https://github.com/zitadel/zitadel/releases/tag/v4.11.0>
456. Zitadel docs (v4.20.0 source): SAML 2.0 endpoints: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/saml/endpoints.mdx?plain=1#L6-L30>
457. Zitadel docs (v4.20.0 source): SAML SSO guide, SP-initiated only: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/login/saml.mdx?plain=1#L64>
458. Zitadel v4.20.0 defaults.yaml: SAML provider configuration: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L718-L726>
459. Zitadel v4.20.0 source: single TCP listener for HTTP/gRPC: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/start/start.go#L763-L769>
460. Zitadel v4.20.0 go.mod: go-ldap client dependency: <https://github.com/zitadel/zitadel/blob/v4.20.0/go.mod#L39>
461. Zitadel docs (v4.20.0 source): LDAP identity provider: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/identity-providers/ldap.mdx?plain=1#L1-L20>
462. Zitadel docs (v4.20.0 source): how the LDAP IdP login works: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/identity-providers/_how_ldap_idp_works.mdx?plain=1#L1-L8>
463. Zitadel docs (v4.20.0 source): SCIM v2.0 limitations (User schema only): <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/user/scim2.mdx?plain=1#L93-L100>
464. Zitadel docs (v4.20.0 source): SCIM API base URL and authentication: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/scim2.mdx?plain=1#L15-L35>
465. Zitadel v4.20.0 source: SCIM server registration: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/start/start.go#L700-L710>
466. Zitadel docs (v4.20.0 source): API and UI path prefixes: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/introduction.mdx?plain=1#L260-L312>
467. Zitadel docs (v4.20.0 source): OAuth2-proxy (third-party) example: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/examples/identity-proxy/oauth2-proxy.mdx?plain=1#L1-L8>
468. Zitadel docs (v4.20.0 source): introspection endpoint: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/endpoints.mdx?plain=1#L453-L504>
469. Zitadel v4.20.0 source: introspection client authentication: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/introspect.go#L139-L172>
470. Zitadel v4.20.0 source: introspection audience check: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/oidc/introspect.go#L232-L240>
471. Zitadel docs (v4.20.0 source): revocation endpoint: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/endpoints.mdx?plain=1#L554-L563>
472. Zitadel docs (v4.20.0 source): opaque tokens are the default: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/concepts/knowledge/opaque-tokens.mdx?plain=1#L8>
473. Zitadel v4.20.0 proto: OIDCTokenType (BEARER = 0, JWT = 1): <https://github.com/zitadel/zitadel/blob/v4.20.0/proto/zitadel/application/v2/oidc.proto#L50-L53>
474. Zitadel docs (v4.20.0 source): application token type setting: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/applications-overview.mdx?plain=1#L201>
475. Zitadel docs (v4.20.0 source): refresh token grant: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/endpoints.mdx?plain=1#L275-L336>
476. Zitadel v4.20.0 source: refresh token exchange renews refresh token: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/oidc_session.go#L196-L221>
477. Zitadel v4.20.0 source: CheckRefreshToken: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/oidc_session_model.go#L146-L158>
478. Zitadel v4.20.0 defaults.yaml: OIDC token lifetimes: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1345-L1351>
479. Zitadel docs (v4.20.0 source): end_session endpoint: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/openidoauth/endpoints.mdx?plain=1#L621-L641>
480. Zitadel docs (v4.20.0 source): OIDC Back-Channel Logout: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/back-channel-logout.mdx?plain=1#L7-L57>
481. Zitadel docs (v4.20.0 source): logout, front-channel not implemented: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/login/oidc/logout.mdx?plain=1#L47-L54>
482. GitHub issue #10239: Implement Pushed Authorization Requests (open): <https://github.com/zitadel/zitadel/issues/10239>
483. GitHub issue #5402: Support DPoP (open): <https://github.com/zitadel/zitadel/issues/5402>
484. Zitadel docs (v4.20.0 source): Management Console overview: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/console-overview.mdx?plain=1#L7-L17>
485. Zitadel docs (v4.20.0 source): APIs introduction: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/introduction.mdx?plain=1#L10>
486. Zitadel docs (v4.20.0 source): access Zitadel APIs: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/zitadel-apis/access-zitadel-apis.mdx?plain=1#L7-L32>
487. Zitadel docs (v4.20.0 source): System API (self-hosted only): <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/zitadel-apis/access-zitadel-system-api.mdx?plain=1#L9>
488. Zitadel v4.20.0 defaults.yaml: DefaultInstance.LoginPolicy: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1282-L1301>
489. Zitadel docs (v4.20.0 source): Login Behavior and Security settings: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/default-settings.mdx?plain=1#L134-L145>
490. Zitadel docs (v4.20.0 source): password reset: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/login-ui/password-reset.mdx?plain=1#L1-L25>
491. Zitadel docs (v4.20.0 source): roles and role assignments: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/roles.mdx?plain=1#L1-L30>
492. Zitadel docs (v4.20.0 source): users overview, no native hierarchy: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/users-overview.mdx?plain=1#L70-L71>
493. Zitadel docs (v4.20.0 source): instances and virtual instances: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/concepts/structure/instance.mdx?plain=1#L13-L37>
494. Zitadel v4.20.0 source: supported IdP types: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/domain/idp.go#L28-L41>
495. Zitadel docs (v4.20.0 source): user metadata: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/customize/user-metadata.mdx?plain=1#L1-L16>
496. Zitadel docs (v4.20.0 source): Terraform provider: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/terraform-provider.mdx?plain=1#L7-L11>
497. zitadel/terraform-provider-zitadel repository: <https://github.com/zitadel/terraform-provider-zitadel>
498. Zitadel v4.20.0 steps.yaml: FirstInstance setup config: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/setup/steps.yaml#L114-L153>
499. Zitadel docs (v4.20.0 source): passkeys and multifactor settings: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/default-settings.mdx?plain=1#L177-L205>
500. Zitadel v4.20.0 source: default second factors and multifactor for new instances: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/instance.go#L386-L392>
501. Zitadel docs (v4.20.0 source): passkeys and passwordless: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/concepts/features/passkeys.mdx?plain=1#L7>
502. Zitadel docs (v4.20.0 source): supported MFA methods: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/integrate/login-ui/mfa.mdx?plain=1#L15-L19>
503. Zitadel docs (v4.20.0 source): SMS, SMTP and HTTP notification providers: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/customize/notification-providers.mdx?plain=1#L7-L13>
504. Zitadel v4.20.0 proto: GenerateRecoveryCodes / RemoveRecoveryCodes: <https://github.com/zitadel/zitadel/blob/v4.20.0/proto/zitadel/user/v2/user_service.proto#L1148-L1177>
505. Zitadel v4.20.0 defaults.yaml: recovery code settings: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1008-L1016>
506. Zitadel v4.20.0 source: Login V1 MFA verify page types: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/ui/login/mfa_verify_handler.go#L64-L93>
507. GitHub issue #12909: Login v2 recovery codes as second factor (open): <https://github.com/zitadel/zitadel/issues/12909>
508. Zitadel v4.9.0 release notes: recovery code MFA support (#9954): <https://github.com/zitadel/zitadel/releases/tag/v4.9.0>
509. Zitadel v4.20.0 source: Login V2 shouldEnforceMFA: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/login/src/lib/mfa-helper.ts#L149-L187>
510. Zitadel v4.20.0 source: LinkSessionToAuthRequest (no MFA re-check): <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/auth_request.go#L87-L135>
511. Zitadel v4.20.0 defaults.yaml: DefaultInstance.Features (LoginV2 Required): <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1466-L1484>
512. Zitadel v4.0.0 release notes: Login V2 as default: <https://github.com/zitadel/zitadel/releases/tag/v4.0.0>
513. Zitadel v4.20.0 defaults.yaml: DefaultInstance.LockoutPolicy: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1324-L1327>
514. Zitadel v4.20.0 source: verifyPasswordWithLockoutPolicy (lock and tarpit): <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/user_human_password.go#L404-L467>
515. Zitadel docs (v4.20.0 source): Lockout settings: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/default-settings.mdx?plain=1#L260-L271>
516. Zitadel v4.20.0 source: failed-check counter and lock state: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/user_human_password_model.go#L111-L121>
517. Zitadel v4.20.0 defaults.yaml: SystemDefaults.Tarpit: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1017-L1025>
518. Zitadel v4.20.0 source: tarpit duration formula: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/config/systemdefaults/tarpit.go#L16-L34>
519. Zitadel v4.20.0 source: Session API password check with tarpit: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/session.go#L77-L87>
520. Zitadel v4.20.0 source: Login V1 password check, tarpit unless IgnoreUnknownUsernames: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/user_human_password.go#L370-L389>
521. Zitadel docs (v4.20.0 source): production checklist, networking: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/productionchecklist.mdx?plain=1#L34-L38>
522. Zitadel docs (v4.20.0 source): production, limits and rate limiting advice: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/production.mdx?plain=1#L202-L204>
523. Zitadel v4.20.0 defaults.yaml: Quotas (disabled): <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1072-L1086>
524. Zitadel docs (v4.20.0 source): Zitadel Cloud rate limit policy: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/legal/policies/rate-limit-policy.mdx?plain=1#L33-L42>
525. Zitadel v4.20.0 defaults.yaml: password complexity and age policy: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1269-L1277>
526. Zitadel docs (v4.20.0 source): password complexity and expiry: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/default-settings.mdx?plain=1#L224-L258>
527. GitHub issue #8034: Password reuse prevention policy (open): <https://github.com/zitadel/zitadel/issues/8034>
528. GitHub issue #6658: CAPTCHA for registration (open): <https://github.com/zitadel/zitadel/issues/6658>
529. GitHub PR #9785: captcha support with reCAPTCHA v2 (closed, not merged): <https://github.com/zitadel/zitadel/pull/9785>
530. Zitadel v4.20.0 defaults.yaml: PasswordHasher and verifiers: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L868-L948>
531. Zitadel docs (v4.20.0 source): password hashing algorithms: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/concepts/architecture/secrets.mdx?plain=1#L68-L90>
532. Zitadel v4.20.0 defaults_fips.yaml: FIPS password hasher: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults_fips.yaml#L1-L8>
533. Zitadel docs (v4.20.0 source): audit trail: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/concepts/features/audit-trail.mdx?plain=1#L7-L10>
534. Zitadel v4.20.0 defaults.yaml: AuditLogRetention: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1540-L1543>
535. Zitadel v4.20.0 source: failed session checks stored as events: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/command/session.go#L377-L381>
536. Zitadel v4.20.0 defaults.yaml: Eventstore (eventstore.events2 table): <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L1088-L1110>
537. Zitadel docs (v4.20.0 source): hardening instance administrators: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/guides/manage/console/administrator-hardening.mdx?plain=1#L22-L70>
538. Zitadel v4.20.0 source: MFA requirement check for Zitadel API tokens: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/authz/repository/eventsourcing/eventstore/token_verifier.go#L179-L210>
539. Zitadel v4.20.0 steps.yaml: first admin user zitadel-admin defaults: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/setup/steps.yaml#L134-L153>
540. Zitadel docs (v4.20.0 source): requirements (PostgreSQL, Redis): <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/requirements.mdx?plain=1#L8-L19>
541. Zitadel docs (v4.20.0 source): database configuration: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/database/index.mdx?plain=1#L17-L24>
542. Zitadel v3.0.0 release notes: AGPL relicense, CockroachDB removed: <https://github.com/zitadel/zitadel/releases/tag/v3.0.0>
543. Zitadel docs (v4.20.0 source): scaling Zitadel: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/updating_scaling.mdx?plain=1#L21-L31>
544. Zitadel v4.20.0 defaults.yaml: caches (experimental, off): <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L290-L300>
545. Zitadel docs (v4.20.0 source): adopt Login V2: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/adopt-login-v2.mdx?plain=1#L7-L49>
546. Zitadel v4.20.0 defaults.yaml: legacy Metrics.Type otel: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L136-L139>
547. Zitadel v4.20.0 defaults.yaml: Instrumentation.Metric exporter: <https://github.com/zitadel/zitadel/blob/v4.20.0/cmd/defaults.yaml#L39-L50>
548. Zitadel v4.20.0 source: legacy metric config mapped to Prometheus exporter: <https://github.com/zitadel/zitadel/blob/v4.20.0/backend/v3/instrumentation/metric.go#L45-L53>
549. Zitadel v4.20.0 source: health, ready and metrics handlers: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/api.go#L320-L335>
550. Zitadel v4.20.0 source: /debug prefix registration: <https://github.com/zitadel/zitadel/blob/v4.20.0/internal/api/api.go#L154>
551. Zitadel docs (v4.20.0 source): metrics endpoint: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/observability/metrics.mdx?plain=1#L7-L16>
552. Zitadel docs (v4.20.0 source): ready and health endpoints: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/apis/observability/health.mdx?plain=1#L9-L25>
553. Zitadel v4.20.0 source: Login V2 /healthy route: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/login/src/app/healthy/route.ts>
554. Zitadel v4.20.0 compose: zitadel-login service and healthcheck: <https://github.com/zitadel/zitadel/blob/v4.20.0/deploy/compose/docker-compose.yml#L123-L145>
555. Zitadel docs (v4.20.0 source): Kubernetes with Helm: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/deploy/kubernetes/index.mdx?plain=1#L11-L55>
556. zitadel/zitadel-charts repository (official Helm chart): <https://github.com/zitadel/zitadel-charts>
557. Zitadel docs (v4.20.0 source): minimum system requirements: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/self-hosting/manage/production.mdx?plain=1#L206-L220>
558. Zitadel v4.20.0 LICENSING.md: <https://github.com/zitadel/zitadel/blob/v4.20.0/LICENSING.md#L1-L30>
559. Zitadel v4.20.0 LICENSE (GNU AGPL v3): <https://github.com/zitadel/zitadel/blob/v4.20.0/LICENSE>
560. Zitadel docs (v4.20.0 source): Cloud and Enterprise service description: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/legal/service-description/cloud-service-description.mdx?plain=1#L15-L35>
561. Zitadel docs (v4.20.0 source): terms of service, company: <https://github.com/zitadel/zitadel/blob/v4.20.0/apps/docs/content/legal/terms-of-service.mdx?plain=1#L13>

### Rauthy 0.37.2

562. Rauthy source v0.37.2: OIDC discovery document built in well_known.rs: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/well_known.rs#L15-L172>
563. Rauthy book (v0.37.2 source): Introduction, features list: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/intro.md#L166-L234>
564. Rauthy source v0.37.2: client_credentials grant: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/grant_types/client_credentials.rs#L15-L39>
565. Rauthy source v0.37.2: POST /oidc/device and optional per-IP rate limit: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L533-L582>
566. Rauthy source v0.37.2: config defaults, device_grant and dpop: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L384-L394>
567. Rauthy book (v0.37.2 source): Token Exchange (RFC 8693): <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/token_exchange.md#L1-L57>
568. Rauthy source v0.37.2: token exchange grant client checks: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/grant_types/token_exchange.rs#L26-L59>
569. Rauthy source v0.37.2: token exchange subject/actor token validation: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/grant_types/token_exchange.rs#L234-L272>
570. Rauthy CHANGELOG v0.36.1: Token Exchange (RFC 8693): <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L1241-L1262>
571. Rauthy source v0.37.2: JWT validation against own JWKS and issuer: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/jwt/src/token.rs#L68-L216>
572. Rauthy source v0.37.2: RFC 8693 token type URNs: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api_types/src/oidc.rs#L108-L145>
573. Rauthy book (v0.37.2 source): Introduction, PAM logins: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/intro.md#L136-L155>
574. Rauthy issue #915: external LDAP as a source of truth (maintainer reply): <https://github.com/sebadob/rauthy/issues/915>
575. Rauthy book (v0.37.2 source): SCIM: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/scim.md#L1-L27>
576. Rauthy book (v0.37.2 source): Forward Authentication: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/forward_auth.md#L95-L116>
577. Rauthy source v0.37.2: per-client forward_auth routes: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/clients.rs#L666-L697>
578. Rauthy source v0.37.2: config defaults, access and auth_headers: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L308-L340>
579. Rauthy source v0.37.2: token introspection and caller auth: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/token_info.rs#L15-L159>
580. Rauthy source v0.37.2: POST /oidc/introspect: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L1109-L1131>
581. Rauthy source v0.37.2: token revocation: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/token_revocation.rs#L15-L135>
582. Rauthy CHANGELOG v0.34.0: Token Revocation: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L2466-L2470>
583. Rauthy source v0.37.2: JWT header types (at+jwt): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/jwt/src/token.rs#L20-L37>
584. Rauthy CHANGELOG v0.37.0: RFC 9068 at+jwt token type: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L338-L354>
585. Rauthy source v0.37.2: refresh token validation and rotation: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/validation.rs#L65-L267>
586. Rauthy source v0.37.2: refresh token delete_checked / finish_rotation: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/refresh_tokens.rs#L82-L120>
587. Rauthy source v0.37.2: refresh token nbf/exp: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/token_set.rs#L499-L512>
588. Rauthy book (v0.37.2 source): Reference Config, [lifetimes]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2125-L2144>
589. Rauthy source v0.37.2: config defaults, lifetimes: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L584-L593>
590. Rauthy book (v0.37.2 source): Reference Config, disable_refresh_token_nbf: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L59-L76>
591. Rauthy book (v0.37.2 source): User Logout: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/logout.md#L43-L100>
592. Rauthy source v0.37.2: GET/POST /oidc/logout: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L760-L811>
593. Rauthy source v0.37.2: config defaults, backchannel_logout: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L341-L348>
594. Rauthy source v0.37.2: client registration fields not supported (request_uris): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api_types/src/clients.rs#L74>
595. Rauthy source v0.37.2: Admin UI route: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/html.rs#L86>
596. Rauthy book (v0.37.2 source): API Keys: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/api_keys.md#L1-L40>
597. Rauthy book (v0.37.2 source): Swagger UI: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/swagger.md#L1-L20>
598. Rauthy source v0.37.2: config defaults, user_registration: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L1340-L1345>
599. Rauthy book (v0.37.2 source): User Registration: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/user_reg.md#L1-L56>
600. Rauthy source v0.37.2: POST /users/register (enable check, PoW): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/users.rs#L403-L455>
601. Rauthy source v0.37.2: POST /users/request_reset: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/users.rs#L2308-L2336>
602. Rauthy book (v0.37.2 source): Passkeys / WebAuthn: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/passkeys.md#L1-L61>
603. Rauthy book (v0.37.2 source): Delegated Group Admins: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/group_admins.md#L1-L81>
604. Rauthy CHANGELOG v0.36.0: Delegated Group Admins: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L1376-L1382>
605. Rauthy source v0.37.2: upstream auth provider types: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api_types/src/auth_providers.rs#L13-L18>
606. Rauthy book (v0.37.2 source): Upstream Authentication Providers: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/auth_providers/index.md#L1-L6>
607. Rauthy source v0.37.2: config defaults, webauthn and atproto: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L1367-L1382>
608. Rauthy book (v0.37.2 source): Custom Scopes and Attributes: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/custom_scopes_attributes.md#L1-L30>
609. Rauthy CHANGELOG v0.30.0: User-Editable custom attributes: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L4643-L4652>
610. Rauthy book (v0.37.2 source): Reference Config, bootstrap_dir files: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L498-L518>
611. Rauthy book (v0.37.2 source): Bootstrapping: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/bootstrap.md#L239-L259>
612. Rauthy source v0.37.2: OTP validation/sending per kind: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/one_time_password.rs#L294-L380>
613. Rauthy source v0.37.2: OtpKind enum: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api_types/src/users.rs#L406-L411>
614. Rauthy book (v0.37.2 source): Reference Config, [otp]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2268-L2324>
615. Rauthy CHANGELOG v0.37.0: Discoverable Credentials: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L687-L716>
616. Rauthy source v0.37.2: config defaults, mfa and otp: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L603-L615>
617. Rauthy CHANGELOG v0.37.0: OTP via E-Mail: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L901-L909>
618. Rauthy source v0.37.2: MFA cookie lets login skip the password: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/authorize.rs#L107-L123>
619. Rauthy source v0.37.2: admin session MFA enforcement: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/principal.rs#L532-L552>
620. Rauthy source v0.37.2: per-client force_mfa: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/clients.rs#L84>
621. Rauthy source v0.37.2: PAM host force_mfa: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/pam/hosts.rs#L24>
622. Rauthy source v0.37.2: login delay and auto IP blacklisting: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/login_delay.rs#L24-L133>
623. Rauthy book (v0.37.2 source): IP Blacklisting thresholds: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/work/ip_blacklist.md#L1-L25>
624. Rauthy CHANGELOG v0.37.0: login delay combines per-IP and per-user counters: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L592-L600>
625. Rauthy source v0.37.2: per-user failed_login_attempts on password check: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/service/src/oidc/authorize.rs#L149-L175>
626. Hiqlite 0.15.3 (Rauthy's locked dependency, same maintainer): counter_add has no TTL: <https://github.com/sebadob/hiqlite/blob/2db4042057ec6845b6d0cc75ed96d29722d77c26/hiqlite/src/client/cache.rs#L437-L461>
627. Rauthy source v0.37.2: credential stuffing detection: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/cred_stuff_detect.rs#L26-L53>
628. Rauthy source v0.37.2: config defaults, cred_stuff_detection: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L359-L363>
629. Rauthy book (v0.37.2 source): Reference Config, [cred_stuff_detection]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L862-L901>
630. Rauthy source v0.37.2: POST /oidc/token and login delay: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L1021-L1072>
631. Rauthy source v0.37.2: IP blacklist middleware (429 for all requests): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/middlewares/src/ip_blacklist.rs#L83-L92>
632. Rauthy source v0.37.2: config defaults, hashing (Argon2id): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L538-L544>
633. Rauthy source v0.37.2: dynamic client registration per-IP rate limit: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/clients_dyn.rs#L86-L112>
634. Rauthy source v0.37.2: config defaults, dynamic_clients: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L395-L412>
635. Rauthy source v0.37.2: POST /pow challenge endpoint: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/generic.rs#L332-L352>
636. Rauthy source v0.37.2: config defaults, suspicious_requests: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L658-L661>
637. Rauthy book (v0.37.2 source): Reference Config, [suspicious_requests]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2598-L2619>
638. Rauthy migrations v0.37.2: default password policy row: <https://github.com/sebadob/rauthy/blob/v0.37.2/migrations/hiqlite/2_init_data.sql#L16>
639. Rauthy source v0.37.2: PasswordPolicy fields: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/password.rs#L111-L121>
640. Rauthy source v0.37.2: password policy enforcement and expiry: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/users.rs#L1520-L1636>
641. Rauthy source v0.37.2: bincode legacy serialization used for config rows: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/common/src/utils.rs#L242-L250>
642. Rauthy source v0.37.2: POST /oidc/authorize requires PoW: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L333-L359>
643. Rauthy source v0.37.2: POST /oidc/device/verify requires PoW: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/oidc.rs#L689-L699>
644. Rauthy source v0.37.2: POST /providers/login requires PoW: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/auth_providers.rs#L147-L156>
645. Rauthy source v0.37.2: PoW creation and single-use check: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/entity/pow.rs#L10-L49>
646. Rauthy source v0.37.2: config defaults, pow: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L628-L631>
647. spow 0.7.0 (Rauthy's locked dependency, same maintainer): SHA-256 challenge and leading-zero-bit check: <https://github.com/sebadob/spow/blob/db9751462ea06fca1605d88737b4a39734a1e4e0/src/pow.rs#L152-L229>
648. Rauthy CHANGELOG v0.29.0: PoW required for LoginRequest and ProviderLoginRequest: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L5124-L5131>
649. Rauthy CHANGELOG v0.31.0: default PoW difficulty 20 -&gt; 19: <https://github.com/sebadob/rauthy/blob/v0.37.2/CHANGELOG.md#L4014-L4018>
650. Rauthy book (v0.37.2 source): Reference Config, [pow]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2410-L2425>
651. Rauthy frontend v0.37.2: fetch and solve PoW in a web worker: <https://github.com/sebadob/rauthy/blob/v0.37.2/frontend/src/utils/pow.ts#L1-L23>
652. Rauthy source v0.37.2: PoW signing secret from active encryption key: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L244>
653. Rauthy source v0.37.2: Argon2id password hasher: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/common/src/password_hasher.rs#L113-L120>
654. Rauthy book (v0.37.2 source): Password Hashing: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/argon2.md#L1-L37>
655. Rauthy source v0.37.2: config defaults, events: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L477-L521>
656. Rauthy book (v0.37.2 source): Logging and Auditing, Event Persistence: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/logging.md#L353-L383>
657. Rauthy source v0.37.2: EventType list: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/events/event.rs#L141-L168>
658. Rauthy book (v0.37.2 source): Reference Config, access log level: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2218-L2237>
659. Rauthy book (v0.37.2 source): Event Persistence prose (31 days): <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/logging.md#L355-L357>
660. Rauthy book (v0.37.2 source): Reference Config, [mfa]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2260-L2266>
661. Rauthy book (v0.37.2 source): Introduction, databases, resources, HA: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/intro.md#L59-L86>
662. Rauthy book (v0.37.2 source): Reference Config, [database]: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L903-L911>
663. Rauthy book (v0.37.2 source): High Availability: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/ha.md#L1-L12>
664. Rauthy book (v0.37.2 source): Kubernetes (no Helm chart): <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/getting_started/k8s.md#L1-L10>
665. Rauthy source v0.37.2: config defaults, server (metrics): <https://github.com/sebadob/rauthy/blob/v0.37.2/src/data/src/rauthy_config.rs#L637-L654>
666. Rauthy book (v0.37.2 source): Reference Config, metrics: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/config/config.md#L2542-L2563>
667. Rauthy source v0.37.2: /ping, /health, /ready handlers: <https://github.com/sebadob/rauthy/blob/v0.37.2/src/api/src/generic.rs#L318-L508>
668. Rauthy book (v0.37.2 source): Kubernetes probes: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/getting_started/k8s.md#L322-L345>
669. Rauthy book (v0.37.2 source): Kubernetes resources: <https://github.com/sebadob/rauthy/blob/v0.37.2/book/src/getting_started/k8s.md#L346-L375>
670. Rauthy v0.37.2 LICENSE (Apache License 2.0): <https://github.com/sebadob/rauthy/blob/v0.37.2/LICENSE>
671. Rauthy v0.37.2 workspace Cargo.toml (version, authors, license): <https://github.com/sebadob/rauthy/blob/v0.37.2/Cargo.toml#L5-L12>
672. rauthy-client Cargo.toml license: <https://github.com/sebadob/rauthy/blob/v0.37.2/rauthy-client/Cargo.toml#L6>
673. Rauthy README v0.37.2: Support and Funding: <https://github.com/sebadob/rauthy/blob/v0.37.2/README.md#L265-L282>
674. Rauthy GitHub release v0.37.2 (2026-10-19): <https://github.com/sebadob/rauthy/releases/tag/v0.37.2>

### Ory Hydra + Kratos v26.2.0

675. Ory Hydra README at v26.2.0: implemented standards and OpenID certification: <https://github.com/ory/hydra/blob/v26.2.0/README.md#L84-L121>
676. Hydra oauth2/handler.go: OIDC discovery metadata built in source: <https://github.com/ory/hydra/blob/v26.2.0/oauth2/handler.go#L511-L558>
677. Kratos config schema: oauth2_provider (Kratos as Hydra login provider): <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L2264-L2276>
678. Hydra fositex/config.go: default fosite grant/handler factories: <https://github.com/ory/hydra/blob/v26.2.0/fositex/config.go#L56-L74>
679. Ory docs: OAuth2 client credentials flow: <https://www.ory.com/docs/oauth2-oidc/client-credentials>
680. Hydra oauth2/handler.go: public and admin route registration: <https://github.com/ory/hydra/blob/v26.2.0/oauth2/handler.go#L87-L134>
681. Ory Hydra v25.4.0 release notes (device authorization grant added): <https://github.com/ory/hydra/releases/tag/v25.4.0>
682. Ory docs: Device Authorization (RFC 8628): <https://www.ory.com/docs/oauth2-oidc/device-authorization>
683. ory/hydra issue #1218 Support RFC8693 Token Exchange (open), maintainer comment: <https://github.com/ory/hydra/issues/1218#issuecomment-1558812978>
684. ory/hydra issue #1218: maintainer confirms the 2.0 notes linked the wrong RFC: <https://github.com/ory/hydra/issues/1218#issuecomment-1335112458>
685. Ory docs: JSON Web Token (JWT) profile for OAuth2 (RFC 7523): <https://www.ory.com/docs/hydra/guides/jwt>
686. Hydra OpenAPI spec at v26.2.0 (all API paths): <https://github.com/ory/hydra/blob/v26.2.0/spec/api.json>
687. Ory Kratos README at v26.2.0: Ory Enterprise License features: <https://github.com/ory/kratos/blob/v26.2.0/README.md#L132-L145>
688. Kratos ui/node/node.go: UI node groups (captcha, saml 'Available in OEL'): <https://github.com/ory/kratos/blob/v26.2.0/ui/node/node.go#L42-L56>
689. Kratos selfservice/strategy/saml: swagger model stubs only: <https://github.com/ory/kratos/blob/v26.2.0/selfservice/strategy/saml/login.go>
690. Ory docs: Organizations for B2B Single Sign-On OIDC and SAML: <https://www.ory.com/docs/kratos/organizations>
691. ory/kratos issue #274 LDAP authentication: maintainer, no plans to implement: <https://github.com/ory/kratos/issues/274#issuecomment-2137604692>
692. ory/kratos issue #274: maintainer, LDAP not planned anytime soon: <https://github.com/ory/kratos/issues/274#issuecomment-3317394208>
693. Ory docs: SCIM (Ory Network, organization level): <https://www.ory.com/docs/kratos/manage-identities/scim>
694. Kratos OpenAPI spec at v26.2.0 (all API paths): <https://github.com/ory/kratos/blob/v26.2.0/spec/api.json>
695. Kratos session/handler.go: /sessions/whoami routes and identity header: <https://github.com/ory/kratos/blob/v26.2.0/session/handler.go#L92-L94>
696. Ory docs: Traefik API gateway (community-contributed integration): <https://www.ory.com/docs/integrates-with/api-gateways/traefik>
697. Hydra oauth2/handler.go: introspection handler: <https://github.com/ory/hydra/blob/v26.2.0/oauth2/handler.go#L1003-L1029>
698. Hydra UPGRADE.md: introspection moved to admin port, access control stripped: <https://github.com/ory/hydra/blob/v26.2.0/UPGRADE.md#L645-L660>
699. Ory docs: Hydra, prepare for production (admin endpoints, HA): <https://www.ory.com/docs/hydra/self-hosted/production>
700. Ory docs: OAuth 2.0 token introspection (internal use only): <https://www.ory.com/docs/hydra/guides/oauth2-token-introspection>
701. Hydra fosite/revoke_handler.go: revocation authenticates the client: <https://github.com/ory/hydra/blob/v26.2.0/fosite/revoke_handler.go#L37-L51>
702. Hydra config schema: strategies.access_token default opaque: <https://github.com/ory/hydra/blob/v26.2.0/spec/config.json#L631-L636>
703. Hydra driver/config/provider.go: access token strategy resolution: <https://github.com/ory/hydra/blob/v26.2.0/driver/config/provider.go#L567-L583>
704. Ory docs: Stateless JWT access tokens (OEL): <https://www.ory.com/docs/self-hosted/oel/oauth2/stateless-jwt>
705. Hydra fosite refresh flow: refresh token reuse detection: <https://github.com/ory/hydra/blob/v26.2.0/fosite/handler/oauth2/flow_refresh.go#L53-L62>
706. Hydra provider.go: graceful refresh token rotation limits: <https://github.com/ory/hydra/blob/v26.2.0/driver/config/provider.go#L770-L783>
707. Hydra config schema: refresh token rotation grace period defaults: <https://github.com/ory/hydra/blob/v26.2.0/spec/config.json#L850-L871>
708. Ory docs: Graceful refresh token rotation: <https://www.ory.com/docs/hydra/guides/graceful-token-refresh>
709. Ory docs: OpenID Connect logout (RP-initiated, front- and back-channel): <https://www.ory.com/docs/oauth2-oidc/oidc-logout>
710. Hydra bundled fosite: PAR handler factory (not used by Hydra): <https://github.com/ory/hydra/blob/v26.2.0/fosite/compose/compose_par.go>
711. ory/hydra issue #3235 Support DPoP (closed as stale): <https://github.com/ory/hydra/issues/3235>
712. Ory Kratos README at v26.2.0: what the Ory Network provides (Ory Console): <https://github.com/ory/kratos/blob/v26.2.0/README.md#L94-L108>
713. Ory docs: API access control for self-hosted Ory servers: <https://www.ory.com/docs/self-hosted/operations/api-access-control>
714. Hydra cmd/server/handler.go: admin server middleware chain (no auth): <https://github.com/ory/hydra/blob/v26.2.0/cmd/server/handler.go#L119-L165>
715. Kratos cmd/daemon/serve.go: admin server middleware chain (no auth): <https://github.com/ory/kratos/blob/v26.2.0/cmd/daemon/serve.go#L148-L175>
716. Kratos config schema: admin host default 0.0.0.0, port 4434: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L2338-L2352>
717. ory/x serve config schema used by Hydra: host default 0.0.0.0: <https://github.com/ory/hydra/blob/v26.2.0/oryx/configx/serve.schema.json#L29-L34>
718. Kratos config schema: registration flow enabled default: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1261-L1270>
719. Kratos config schema: recovery flow defaults: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1394-L1433>
720. Ory docs: Account recovery and password reset: <https://www.ory.com/docs/kratos/self-service/flows/account-recovery-password-reset>
721. Kratos identity/identity.go: Identity struct fields: <https://github.com/ory/kratos/blob/v26.2.0/identity/identity.go#L52>
722. Ory docs: Role Based Access Control with Ory Keto: <https://www.ory.com/docs/keto/guides/rbac>
723. Ory docs: Introduction to Ory Enterprise License: <https://www.ory.com/docs/oel/getting-started>
724. Kratos config schema: organizations key 'Only effective in the Ory Network': <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L3086-L3091>
725. Kratos config schema: b2b SSO 'not available in the open source licensed code': <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1462-L1465>
726. Ory Hydra README at v26.2.0: open source vs Ory Enterprise License: <https://github.com/ory/hydra/blob/v26.2.0/README.md#L170-L196>
727. Kratos config schema: upstream OIDC provider enum: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L441-L468>
728. Kratos config schema: oidc method enabled default: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1965-L1975>
729. Ory docs: Identity schema: <https://www.ory.com/docs/kratos/manage-identities/identity-schema>
730. Ory Terraform provider README: Ory Network only, no self-hosted support: <https://github.com/ory/terraform-provider-ory/blob/v26.3.9/README.md#L11>
731. Hydra CLI: import oauth2-client from files: <https://github.com/ory/hydra/blob/v26.2.0/cmd/cmd_import_client.go#L24-L26>
732. Kratos CLI: import identities from files: <https://github.com/ory/kratos/blob/v26.2.0/cmd/identities/import.go#L33-L34>
733. Kratos config schema: totp method enabled default: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1752-L1760>
734. Kratos driver/config/config.go: strategies enabled by default: <https://github.com/ory/kratos/blob/v26.2.0/driver/config/config.go#L814-L822>
735. Kratos config schema: webauthn method and passwordless flag: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1786-L1803>
736. Kratos config.go: WebAuthnForPasswordless default false: <https://github.com/ory/kratos/blob/v26.2.0/driver/config/config.go#L1489-L1491>
737. Kratos config schema: passkey method enabled default: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1905-L1913>
738. Ory docs: Passkeys and WebAuthn: <https://www.ory.com/docs/network/kratos/passwordless/passkeys>
739. Kratos config schema: code method (passwordless_enabled, mfa_enabled): <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1546-L1597>
740. Kratos config schema: courier channels (sms over http only): <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L2234-L2257>
741. Kratos config schema: lookup_secret method enabled default: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1775-L1783>
742. Kratos lookup strategy: number and format of recovery codes: <https://github.com/ory/kratos/blob/v26.2.0/selfservice/strategy/lookup/settings.go#L45>
743. Kratos config schema: featureRequiredAal default highest_available: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L877-L883>
744. Ory docs: Step-up authentication (required_aal): <https://www.ory.com/docs/network/kratos/mfa/step-up-authentication>
745. ory/kratos issue #3062: maintainer on requiring 2FA setup (app-side): <https://github.com/ory/kratos/issues/3062#issuecomment-1414436840>
746. Ory docs: Threat models and security profiles (brute force, bots): <https://www.ory.com/docs/kratos/concepts/security>
747. Kratos persister_code.go: one-time code submission limit: <https://github.com/ory/kratos/blob/v26.2.0/persistence/sql/persister_code.go#L46-L66>
748. Kratos config.go: code max_submissions default 5: <https://github.com/ory/kratos/blob/v26.2.0/driver/config/config.go#L1328-L1330>
749. Ory docs: Code submissions limit: <https://www.ory.com/docs/identities/sign-in/code-submission-limit>
750. Ory docs: Ory Network rate limiting: <https://www.ory.com/docs/guides/rate-limits>
751. Hydra fosite rfc8628: ShouldRateLimit always false: <https://github.com/ory/hydra/blob/v26.2.0/fosite/handler/rfc8628/strategy_hmacsha.go#L98-L101>
752. Kratos config schema: password method policy options and defaults: <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L1627-L1679>
753. Kratos password validator: length, similarity, HIBP checks: <https://github.com/ory/kratos/blob/v26.2.0/selfservice/strategy/password/validator.go#L175-L216>
754. Ory docs: Password policy: <https://www.ory.com/docs/concepts/password-policy>
755. Kratos hasher_bcrypt.go: 72-byte password limit: <https://github.com/ory/kratos/blob/v26.2.0/hash/hasher_bcrypt.go#L62-L69>
756. Ory docs: CAPTCHA challenge (plan required, Cloudflare Turnstile): <https://www.ory.com/docs/kratos/self-service/flows/CAPTCHA>
757. Kratos config schema: hashers (algorithm, argon2, bcrypt): <https://github.com/ory/kratos/blob/v26.2.0/embedx/config.schema.json#L2670-L2745>
758. Kratos config.go: argon2 and bcrypt hasher parameters: <https://github.com/ory/kratos/blob/v26.2.0/driver/config/config.go#L535-L561>
759. Kratos registry_default.go: hasher selection: <https://github.com/ory/kratos/blob/v26.2.0/driver/registry_default.go#L490-L497>
760. Kratos config.go: DefaultPasswordHashingAlgorithm constant: <https://github.com/ory/kratos/blob/v26.2.0/driver/config/config.go#L52>
761. ory/x configx provider: JSON schema defaults loaded first: <https://github.com/ory/kratos/blob/v26.2.0/oryx/configx/provider.go#L71-L78>
762. Kratos login test: imported hash upgraded to bcrypt by default: <https://github.com/ory/kratos/blob/v26.2.0/selfservice/strategy/password/login_test.go#L896-L902>
763. Kratos x/events: emitted event names: <https://github.com/ory/kratos/blob/v26.2.0/x/events/events.go#L23-L52>
764. Kratos login hook: success log line and span event: <https://github.com/ory/kratos/blob/v26.2.0/selfservice/flow/login/hook.go#L266-L272>
765. Hydra x/events: events emitted as OpenTelemetry span events: <https://github.com/ory/hydra/blob/v26.2.0/x/events/events.go#L147-L153>
766. Ory docs: Live event streams (Ory Network enterprise): <https://www.ory.com/docs/actions/live-events>
767. Kratos registry_default.go: Audit() logger definition: <https://github.com/ory/kratos/blob/v26.2.0/driver/registry_default.go#L167-L168>
768. ory/x otelx tracing config schema: provider has no default: <https://github.com/ory/kratos/blob/v26.2.0/oryx/otelx/config.schema.json#L8-L13>
769. Ory docs: Database (deployment fundamentals for Ory OSS): <https://www.ory.com/docs/oss/deployment>
770. Ory docs: Kratos, go to production: <https://www.ory.com/docs/kratos/guides/production>
771. Ory docs: Hydra database setup and configuration: <https://www.ory.com/docs/hydra/self-hosted/dependencies-environment>
772. Ory docs: Scalability (self-hosted): <https://www.ory.com/docs/self-hosted/operations/scalability>
773. Ory docs: Observability (Prometheus endpoints): <https://www.ory.com/docs/self-hosted/operations/observability>
774. Hydra registry_sql.go: public/admin routes incl. health and Prometheus: <https://github.com/ory/hydra/blob/v26.2.0/driver/registry_sql.go#L317-L336>
775. Kratos registry_default.go: public/admin routes incl. health and Prometheus: <https://github.com/ory/kratos/blob/v26.2.0/driver/registry_default.go#L170-L227>
776. ory/x healthx: alive and ready endpoint semantics: <https://github.com/ory/hydra/blob/v26.2.0/oryx/healthx/handler.go#L108-L156>
777. ory/k8s Helm chart for Hydra (appVersion v26.2.0): <https://github.com/ory/k8s/blob/v0.64.0/helm/charts/hydra/Chart.yaml#L3>
778. ory/k8s Helm chart for Kratos (appVersion v26.2.0): <https://github.com/ory/k8s/blob/v0.64.0/helm/charts/kratos/Chart.yaml#L3>
779. Ory docs: Hydra Kubernetes Helm Chart: <https://www.ory.com/docs/hydra/self-hosted/kubernetes-helm-chart>
780. Ory docs: Ory is open source (projects, Helm charts, Terraform provider): <https://www.ory.com/docs/oss/open-source>
781. Ory Hydra LICENSE at v26.2.0: <https://github.com/ory/hydra/blob/v26.2.0/LICENSE>
782. Ory Kratos LICENSE at v26.2.0: <https://github.com/ory/kratos/blob/v26.2.0/LICENSE>
783. oryx/reqlog LICENSE (MIT) bundled in both repos: <https://github.com/ory/kratos/blob/v26.2.0/oryx/reqlog/LICENSE>
784. Ory docs: Upgrade Ory Hydra OEL (OEL image tag list): <https://www.ory.com/docs/self-hosted/oel/oauth2/upgrade>
785. Ory Hydra MAINTAINERS at v26.2.0: <https://github.com/ory/hydra/blob/v26.2.0/MAINTAINERS>

### Casdoor v4.24.0

786. Casdoor v4.24.0 source: OIDC discovery document (object/wellknown_oidc_discovery.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/wellknown_oidc_discovery.go#L31-L212>
787. Casdoor v4.24.0 source: OAuth, well-known, CAS and SCIM routes (routers/router.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/routers/router.go#L383-L432>
788. Casdoor v4.24.0 source: built-in signing cert generated on first start (object/init.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/init.go#L344-L371>
789. Casdoor docs: Standard OIDC client (discovery endpoints): <https://casdoor.ai/docs/how-to-connect/oidc-client>
790. Casdoor v4.24.0 source: token endpoint grant dispatch and DPoP binding (object/token_oauth.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_oauth.go#L85-L137>
791. Casdoor v4.24.0 source: IsGrantTypeValid (object/token_oauth_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_oauth_util.go#L249-L259>
792. Casdoor v4.24.0 source: admin console defaults for a new application (web/src/pages/defaults.ts): <https://github.com/casdoor/casdoor/blob/v4.24.0/web/src/pages/defaults.ts#L54-L108>
793. Casdoor v4.24.0 source: built-in application app-built-in created on first start (object/init.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/init.go#L294-L337>
794. Casdoor docs: OAuth 2.0 (grant types, device grant, refresh rotation, token exchange, DPoP, introspection): <https://casdoor.ai/docs/how-to-connect/oauth>
795. Casdoor v4.24.0 source: DeviceAuth endpoint (controllers/auth.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/auth.go#L1852-L1881>
796. Casdoor v4.24.0 source: Redis-backed device authorization store (object/device_auth_store.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/device_auth_store.go#L41-L60>
797. Casdoor v4.24.0 source: RFC 8693 token exchange (object/token_oauth.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_oauth.go#L738-L939>
798. Casdoor v4.24.0 source: federated credentials for external OIDC issuers (object/token_federated.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_federated.go#L32-L41>
799. Casdoor v4.19.0 release notes (initAdminPassword/welcome page, external OIDC federated credentials, refresh rotation opt-out): <https://github.com/casdoor/casdoor/releases/tag/v4.19.0>
800. Casdoor docs: Casdoor as a SAML 2.0 identity provider: <https://casdoor.ai/docs/how-to-connect/saml/overview>
801. Casdoor v4.24.0 source: SAML routes (routers/router.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/routers/router.go#L60-L64>
802. Casdoor v4.24.0 source: SAML IdP-initiated request and response (object/saml_idp.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/saml_idp.go#L406-L434>
803. Casdoor v4.24.0 source: SAML SP for upstream SAML providers (object/saml_sp.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/saml_sp.go#L54>
804. Casdoor v4.24.0 source: built-in LDAP server start (ldap/server.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/ldap/server.go#L30-L51>
805. Casdoor v4.24.0 source: shipped conf/app.conf LDAP and RADIUS settings: <https://github.com/casdoor/casdoor/blob/v4.24.0/conf/app.conf#L32-L37>
806. Casdoor v4.24.0 source: main.go starts LDAP and RADIUS servers: <https://github.com/casdoor/casdoor/blob/v4.24.0/main.go#L155-L156>
807. Casdoor docs: LDAP server: <https://casdoor.ai/docs/ldap/ldapserver>
808. Casdoor docs: LDAP overview (sync and authentication): <https://casdoor.ai/docs/ldap/overview>
809. Casdoor v4.24.0 source: LDAP source configuration (object/ldap.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/ldap.go#L21-L45>
810. Casdoor v4.24.0 source: CheckLdapUserPassword bind (object/check.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check.go#L331-L395>
811. Casdoor v4.24.0 source: SCIM handler requires admin (controllers/scim.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/scim.go#L23-L32>
812. Casdoor v4.24.0 source: SCIM syncer is read-only (object/syncer_scim.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/syncer_scim.go#L45-L55>
813. Casdoor docs: SCIM overview: <https://casdoor.ai/docs/scim/overview>
814. Casdoor docs: Feature comparison (Casdoor, Keycloak, ZITADEL, authentik): <https://casdoor.ai/docs/comparison/feature-comparison>
815. Casdoor v4.24.0 source: RADIUS server and per-organization Enable RADIUS check (radius/server.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/radius/server.go#L72-L127>
816. Casdoor docs: RADIUS overview: <https://casdoor.ai/docs/radius/overview>
817. Casdoor v4.24.0 source: forward auth handler (service/forward_auth.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/service/forward_auth.go#L66-L147>
818. Casdoor v4.24.0 source: /api/forward-auth filter registration (main.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/main.go#L112>
819. Casdoor docs: Sites, including forward auth for Traefik, Caddy and Nginx: <https://casdoor.ai/docs/site/overview>
820. Casdoor v4.20.0 release notes (adds forward auth endpoint): <https://github.com/casdoor/casdoor/releases/tag/v4.20.0>
821. Casdoor v4.24.0 source: IntrospectToken (controllers/token.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/token.go#L604-L748>
822. Casdoor v4.24.0 source: ValidateOAuth client authentication (controllers/token.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/token.go#L540-L602>
823. Casdoor v4.24.0 source: RevokeToken endpoint (controllers/token.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/token.go#L473-L529>
824. Casdoor v4.24.0 source: RevokeToken logic (object/token_oauth_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_oauth_util.go#L365-L401>
825. Casdoor v4.23.0 release notes (adds RFC 7009 token revocation endpoint): <https://github.com/casdoor/casdoor/releases/tag/v4.23.0>
826. Casdoor v4.24.0 source: token formats (object/token_jwt.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_jwt.go#L705-L731>
827. Casdoor docs: Tokens (formats, lifecycle, custom attributes): <https://casdoor.ai/docs/token/overview>
828. Casdoor v4.24.0 source: built-in organization created on first start (object/init.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/init.go#L135-L158>
829. Casdoor v4.24.0 source: RefreshToken and rotation (object/token_oauth_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_oauth_util.go#L569-L777>
830. Casdoor v4.24.0 source: Logout (end-session) parameters (controllers/account.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/account.go#L401-L406>
831. Casdoor docs: RP-initiated logout: <https://casdoor.ai/docs/session/rp-initiated-logout>
832. Casdoor v4.24.0 source: OIDC back-channel logout (object/token_logout.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_logout.go#L81-L120>
833. Casdoor docs: Single sign-out (OIDC back-channel logout): <https://casdoor.ai/docs/session/single-sign-out>
834. Casdoor docs: Casdoor vs Keycloak (PAR, UMA, FAPI only in Keycloak): <https://casdoor.ai/docs/comparison/casdoor-vs-keycloak>
835. Casdoor v4.24.0 source: DPoP proof validation (object/token_dpop.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/token_dpop.go#L30-L139>
836. Casdoor v4.24.0 source: admin console frontend (web/): <https://github.com/casdoor/casdoor/tree/v4.24.0/web>
837. Casdoor docs: Admin console: <https://casdoor.ai/docs/basic/admin-console>
838. Casdoor v4.24.0 README (Casdoor Cloud is the same open-source Casdoor; Redis for multiple replicas): <https://github.com/casdoor/casdoor/blob/v4.24.0/README.md#L106>
839. Casdoor v4.24.0 source: API request authentication methods (routers/auto_signin_filter.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/routers/auto_signin_filter.go#L50-L175>
840. Casdoor docs: Call the Casdoor API (authentication methods): <https://casdoor.ai/docs/basic/public-api>
841. Casdoor v4.24.0 source: IsSelfSignupEnabled and IsSignupAllowedFor (object/application_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/application_util.go#L840-L852>
842. Casdoor v4.24.0 source: Signup checks (controllers/account.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/account.go#L104-L114>
843. Casdoor v4.24.0 source: forgot-password verification codes (controllers/verification.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/verification.go#L216-L230>
844. Casdoor docs: Sign-in items, forgot-password flow: <https://casdoor.ai/docs/application/signin-items-table>
845. Casdoor docs: Email providers (password reset link): <https://casdoor.ai/docs/provider/email/overview>
846. Casdoor v4.24.0 source: Group with ParentId (object/group.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/group.go#L38-L41>
847. Casdoor v4.24.0 source: Role members (object/role.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/role.go#L36-L39>
848. Casdoor docs: Roles: <https://casdoor.ai/docs/user/roles>
849. Casdoor v4.24.0 source: Organization object (object/organization.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/organization.go#L52-L121>
850. Casdoor docs: Organizations (password storage types, bcrypt default): <https://casdoor.ai/docs/organization/overview>
851. Casdoor docs: Records (audit log): <https://casdoor.ai/docs/organization/records>
852. Casdoor v4.24.0 source: upstream identity provider types (idp/provider.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/idp/provider.go#L69-L205>
853. Casdoor docs: OAuth providers: <https://casdoor.ai/docs/provider/oauth/overview>
854. Casdoor v4.24.0 source: User.Properties map (object/user.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/user.go#L236>
855. Casdoor docs: Users (Properties field): <https://casdoor.ai/docs/user/overview>
856. Casdoor v4.24.0 source: init data file options (object/init_data.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/init_data.go#L64-L97>
857. Casdoor v4.24.0 README: official Terraform provider: <https://github.com/casdoor/casdoor/blob/v4.24.0/README.md#L191>
858. Casdoor docs: Manage Casdoor with Terraform (official provider): <https://casdoor.ai/docs/deployment/terraform>
859. Casdoor docs: Kubernetes operator: <https://casdoor.ai/docs/deployment/kubernetes-operator>
860. GitHub: casdoor/casdoor-operator (first-party Kubernetes operator): <https://github.com/casdoor/casdoor-operator>
861. Casdoor v4.24.0 source: MFA types (object/mfa.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/mfa.go#L41-L68>
862. Casdoor docs: Multi-factor authentication: <https://casdoor.ai/docs/user/multi-factor-authentication>
863. Casdoor v4.24.0 source: frontend MFA type constants: <https://github.com/casdoor/casdoor/blob/v4.24.0/web/src/components/auth/mfa/constants.ts#L1-L7>
864. Casdoor v4.24.0 source: WebAuthn sign-in with discoverable login (controllers/webauthn.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/webauthn.go#L123-L163>
865. Casdoor v4.24.0 source: sign-in method tabs on the login page (web/src/pages/auth/LoginPage.tsx): <https://github.com/casdoor/casdoor/blob/v4.24.0/web/src/pages/auth/LoginPage.tsx#L80-L92>
866. Casdoor docs: Set up WebAuthn sign-in: <https://casdoor.ai/docs/how-to-connect/webauthn>
867. Casdoor docs: Sign-in methods: <https://casdoor.ai/docs/application/signin-methods>
868. Casdoor v4.24.0 source: MFA setup recovery code (controllers/mfa.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/mfa.go#L80-L91>
869. Casdoor v4.24.0 source: MfaRecover (object/mfa.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/mfa.go#L94-L118>
870. Casdoor v4.24.0 source: MFA items and required MFA (object/organization.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/organization.go#L778-L822>
871. Casdoor docs: Require multi-factor authentication (MFA items): <https://casdoor.ai/docs/organization/mfa-items>
872. Casdoor v4.24.0 source: default failed sign-in limit and frozen time (object/check.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check.go#L32-L35>
873. Casdoor v4.24.0 source: checkSigninErrorTimes and captcha bypass (object/check.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check.go#L232-L274>
874. Casdoor v4.24.0 source: per-application lockout config and failure counter (object/check_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check_util.go#L69-L125>
875. Casdoor v4.24.0 source: per-IP verification code attempt limits (object/verification_ip.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/verification_ip.go#L28-L33>
876. Casdoor docs: Application settings reference (failed sign-in limit and frozen time): <https://casdoor.ai/docs/application/terminology>
877. Casdoor v4.24.0 source: password login with captcha check (controllers/auth.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/auth.go#L933-L990>
878. Casdoor v4.24.0 source: verification code resend throttle (object/verification.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/verification.go#L83-L111>
879. Casdoor v4.24.0 source: IP rate limiting rule for Sites (rule/rule_ip_rate.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/rule/rule_ip_rate.go#L31-L130>
880. Casdoor docs: Rules (traffic rules for Sites): <https://casdoor.ai/docs/rule/overview>
881. Casdoor docs: IP allowlist and verification code rate limiting: <https://casdoor.ai/docs/ip-whitelist>
882. Casdoor v4.24.0 source: admin console defaults for a new organization: <https://github.com/casdoor/casdoor/blob/v4.24.0/web/src/pages/organization-defaults.ts#L7-L39>
883. Casdoor v4.24.0 source: password complexity options (object/check_password_complexity.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check_password_complexity.go#L32-L99>
884. Casdoor docs: Password complexity, history and expiry: <https://casdoor.ai/docs/organization/passwordComplexity>
885. Casdoor v4.24.0 source: captcha provider types (captcha/provider.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/captcha/provider.go#L25-L40>
886. Casdoor v4.24.0 source: captcha rules Always, Dynamic, Internet-Only (object/check.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/check.go#L992-L1030>
887. Casdoor docs: Captcha providers: <https://casdoor.ai/docs/provider/captcha/overview>
888. Casdoor v4.24.0 source: AddOrganization defaults password type to bcrypt (object/organization.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/organization.go#L362-L395>
889. Casdoor v4.24.0 source: password hash types (cred/manager.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/cred/manager.go#L22-L41>
890. Casdoor v4.24.0 source: bcrypt with bcrypt.DefaultCost (cred/bcrypt.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/cred/bcrypt.go#L12-L18>
891. golang.org/x/crypto v0.55.0 (version pinned in Casdoor go.mod): bcrypt DefaultCost = 10: <https://github.com/golang/crypto/blob/v0.55.0/bcrypt/bcrypt.go#L24>
892. Casdoor v4.24.0 source: argon2id with argon2id.DefaultParams (cred/argon2id.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/cred/argon2id.go#L26-L32>
893. alexedwards/argon2id at the commit pinned in Casdoor go.mod: DefaultParams (64 MiB, 1 iteration, parallelism 2): <https://github.com/alexedwards/argon2id/blob/3585854a6387/argon2id.go#L45-L51>
894. Casdoor v4.24.0 source: pbkdf2-salt with 27500 iterations of SHA-256 (cred/pbkdf2-salt.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/cred/pbkdf2-salt.go#L31-L36>
895. Casdoor v4.24.0 source: UpdateUserPassword (empty org password type stores plain) (object/user_cred.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/user_cred.go#L45-L70>
896. Casdoor commit: use bcrypt password type by default for all organizations (#4654): <https://github.com/casdoor/casdoor/commit/eb60e431926770d71c07fb81ea41f4b2cb6be7ed>
897. Casdoor v4.24.0 source: conf/app.conf logPostOnly = true: <https://github.com/casdoor/casdoor/blob/v4.24.0/conf/app.conf#L17>
898. Casdoor v4.24.0 source: AddRecord audit log (object/record.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/record.go#L240-L266>
899. Casdoor v4.24.0 source: record retention (object/record_cleanup.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/record_cleanup.go#L33-L50>
900. Casdoor v4.24.0 source: global default record retention days (object/setting.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/setting.go#L42-L43>
901. Casdoor v4.24.0 release notes: <https://github.com/casdoor/casdoor/releases/tag/v4.24.0>
902. Casdoor v4.24.0 source: admin-only user fields incl. MfaItems (object/user_util.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/user_util.go#L621-L631>
903. Casdoor v4.24.0 source: compiled-in database drivers (object/ormer.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/object/ormer.go#L25-L36>
904. Casdoor docs: Server installation (supported databases): <https://casdoor.ai/docs/basic/server-installation>
905. Casdoor v4.24.0 source: session store, file unless Redis (main.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/main.go#L45-L52>
906. Casdoor docs: CAS (tickets kept in memory): <https://casdoor.ai/docs/how-to-connect/cas>
907. Casdoor docs: Configuration reference (initAdminPassword, isDemoMode, redisEndpoint): <https://casdoor.ai/docs/basic/configuration>
908. Casdoor v4.24.0 source: /api/metrics authorization (controllers/prometheus.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/prometheus.go#L41-L63>
909. Casdoor v4.24.0 source: /api/health and /api/metrics routes (routers/router.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/routers/router.go#L325-L327>
910. Casdoor docs: Prometheus: <https://casdoor.ai/docs/monitoring/Prometheus>
911. Casdoor v4.24.0 source: Health endpoint (controllers/system_info.go): <https://github.com/casdoor/casdoor/blob/v4.24.0/controllers/system_info.go#L117-L125>
912. Casdoor v4.24.0 source: Helm chart probe path (manifests/casdoor/values.yaml): <https://github.com/casdoor/casdoor/blob/v4.24.0/manifests/casdoor/values.yaml#L115-L117>
913. Casdoor v4.24.0 source: Helm chart (manifests/casdoor/Chart.yaml): <https://github.com/casdoor/casdoor/blob/v4.24.0/manifests/casdoor/Chart.yaml>
914. Casdoor v4.24.0 README: helm install from oci://ghcr.io/casdoor/helm-charts/casdoor: <https://github.com/casdoor/casdoor/blob/v4.24.0/README.md#L169>
915. Casdoor docs: Try with Helm: <https://casdoor.ai/docs/basic/try-with-helm>
916. Casdoor docs: Try with Docker (RAM requirements): <https://casdoor.ai/docs/basic/try-with-docker>
917. Casdoor v4.24.0 source: Helm chart default resources {} (manifests/casdoor/values.yaml): <https://github.com/casdoor/casdoor/blob/v4.24.0/manifests/casdoor/values.yaml#L253>
918. Casdoor v4.24.0 LICENSE (Apache License 2.0): <https://github.com/casdoor/casdoor/blob/v4.24.0/LICENSE>
919. Casdoor Cloud pricing and FAQ (operated by Casbin Inc.): <https://www.casdoor.com/pricing>
920. GitHub: casdoor/casdoor contributors: <https://github.com/casdoor/casdoor/graphs/contributors>

### Logto v1.45.0

921. Logto v1.45.0 source: OIDC provider construction and enabled features (init.ts): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/init.ts#L173-L227>
922. Logto v1.45.0 integration test: reviewed OIDC discovery metadata snapshot (dev features disabled): <https://github.com/logto-io/logto/blob/v1.45.0/packages/integration-tests/src/tests/api/oidc/discovery.test.ts#L30-L146>
923. Logto docs: Core service, enabled OpenID features: <https://docs.logto.io/concepts/core-service>
924. Logto v1.45.0 packages/core/package.json: oidc-provider pinned to logto-io fork commit: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/package.json#L88>
925. Logto docs: Machine-to-machine quick start (client credentials): <https://docs.logto.io/quick-starts/m2m>
926. Logto v1.45.0 source: deviceFlowConfig enabled: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/device-flow.ts#L135-L136>
927. Logto core CHANGELOG 1.38.0: support OAuth 2.0 Device Authorization Grant: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L641>
928. Logto docs: Device flow quick start: <https://docs.logto.io/quick-starts/device-flow>
929. Logto v1.45.0 source: allowTokenExchange and isDeviceFlow client metadata (default false): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/foundations/jsonb-types/oidc-module.ts#L83-L98>
930. Logto v1.45.0 source: token exchange subject token types: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/grants/token-exchange/types.ts#L11-L27>
931. Logto v1.45.0 source: token exchange subject token validation: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/grants/token-exchange/account.ts#L174-L213>
932. Logto v1.45.0 source: token exchange JWT verification uses local JWKS and issuer: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/grants/token-exchange/index.ts#L119-L121>
933. Logto docs: User impersonation (token exchange): <https://docs.logto.io/developers/user-impersonation>
934. Logto docs: Service-to-service delegation (token exchange): <https://docs.logto.io/developers/service-to-service-delegation>
935. Logto core CHANGELOG 1.36.0: token exchange with app-level control: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L879-L885>
936. Logto docs: SAML app (Logto as SAML IdP): <https://docs.logto.io/integrate-logto/saml-app>
937. Logto v1.45.0 source: ossDefaultQuota (entitlements without a license): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/consts/license.ts#L118-L133>
938. Logto v1.45.0 source: OSS quota guard (only SAML cap and IdP-initiated SSO enforced): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/libraries/quota.ts#L152-L168>
939. Logto docs: Logto OSS, feature supported by Logto OSS (Cloud-exclusive list): <https://docs.logto.io/logto-oss>
940. logto-io/logto issue #7560: feature request built-in LDAP server, maintainer reply: <https://github.com/logto-io/logto/issues/7560#issuecomment-3082574006>
941. logto-io/logto issue #1588: maintainer, no plan for a native LDAP connector: <https://github.com/logto-io/logto/issues/1588#issuecomment-6336927829>
942. Logto v1.45.0 source: enterprise SSO provider names: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/types/sso-connector.ts#L21-L28>
943. Logto docs: Enterprise connectors (OIDC, SAML, Entra ID, Okta, Google Workspace): <https://docs.logto.io/connectors/enterprise-connectors>
944. logto-io/logto issue #9331: maintainer, SCIM support on roadmap: <https://github.com/logto-io/logto/issues/9331#issuecomment-5882473897>
945. Logto v1.45.0 source: Protected app guide metadata isCloud: true: <https://github.com/logto-io/logto/blob/v1.45.0/packages/console/src/assets/docs/guides/protected-app/index.ts#L5-L12>
946. Logto docs: Protected App (Cloudflare-based): <https://docs.logto.io/integrate-logto/protected-app>
947. Logto docs: Opaque token and introspection endpoint: <https://docs.logto.io/concepts/opaque-token>
948. Logto node-oidc-provider fork (pinned commit): default introspection allowedPolicy: <https://github.com/logto-io/node-oidc-provider/blob/513c523c0e68ee6112da8c871cce86204a136163/lib/helpers/defaults.js#L189-L201>
949. Logto node-oidc-provider fork (pinned commit): JWTs rejected at introspection/revocation: <https://github.com/logto-io/node-oidc-provider/blob/513c523c0e68ee6112da8c871cce86204a136163/lib/shared/reject_structured_tokens.js#L5-L17>
950. Logto core CHANGELOG 1.42.0: upgrade to node-oidc-provider v9 (revocation changes): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L264-L272>
951. Logto v1.45.0 source: resource server accessTokenFormat jwt: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/resource.ts#L15-L22>
952. Logto docs: Role-based access control (global and organization roles, token format): <https://docs.logto.io/authorization/role-based-access-control>
953. Logto v1.45.0 source: customClientMetadataDefault (rotateRefreshToken true, 14-day refresh TTL): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/consts/oidc.ts#L14-L18>
954. Logto v1.45.0 source: rotateRefreshToken hook: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/init.ts#L564-L575>
955. Logto v1.45.0 source: refresh token rotation policy: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/defaults.ts#L23-L41>
956. Logto v1.45.0 source: refresh token grant, reuse detection and rotation: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/grants/refresh-token.ts#L213-L265>
957. Logto docs: Application data structure, rotate refresh token: <https://docs.logto.io/integrate-logto/application-data-structure#rotate-refresh-token>
958. Logto docs: Sign-out (end session, back-channel logout): <https://docs.logto.io/end-user-flows/sign-out>
959. Logto node-oidc-provider fork (pinned commit): pushedAuthorizationRequests enabled by default: <https://github.com/logto-io/node-oidc-provider/blob/513c523c0e68ee6112da8c871cce86204a136163/lib/helpers/defaults.js#L1818-L1819>
960. Logto v1.45.0 source: DPoP explicitly disabled: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/oidc/init.ts#L219-L223>
961. Logto docs: Core service configuration (environment variables): <https://docs.logto.io/concepts/core-service/configuration>
962. Logto docs: Self-hosted license: <https://docs.logto.io/logto-oss/self-hosted-license>
963. Logto docs: Interact with Management API: <https://docs.logto.io/integrate-logto/interact-with-management-api>
964. Logto v1.45.0 source: API routers (audit log middleware, Management API auth): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/routes/init.ts#L65-L73>
965. Logto v1.45.0 source: default sign-in experience seed: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/seeds/sign-in-experience.ts#L39-L65>
966. Logto v1.45.0 schema: sign_in_experiences column defaults: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/sign_in_experiences.sql#L20-L38>
967. Logto docs: Disable user registration: <https://docs.logto.io/end-user-flows/sign-up-and-sign-in/disable-user-registration>
968. Logto docs: Reset password: <https://docs.logto.io/end-user-flows/sign-up-and-sign-in/reset-password>
969. Logto v1.45.0 source: forgot password availability: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/libraries/sign-in-experience/index.ts#L35-L53>
970. Logto v1.45.0 schema: role types: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/roles.sql#L3>
971. Logto docs: Organizations: <https://docs.logto.io/organizations>
972. Logto docs: Social connectors: <https://docs.logto.io/connectors/social-connectors>
973. Logto v1.45.0 schema: users profile and custom_data columns: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/users.sql#L18-L22>
974. Logto docs: User data, custom data: <https://docs.logto.io/user-management/user-data>
975. Logto docs: Collect user profile: <https://docs.logto.io/end-user-flows/collect-user-profile>
976. logto-io/logto issue #6552: Terraform support closed citing community provider: <https://github.com/logto-io/logto/issues/6552#issuecomment-6261970698>
977. Logto v1.45.0 source: MFA factors and MFA policies: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/foundations/jsonb-types/sign-in-experience.ts#L180-L214>
978. Logto docs: Authenticator app OTP: <https://docs.logto.io/end-user-flows/mfa/authenticator-app-otp>
979. Logto docs: Passkeys (WebAuthn) MFA: <https://docs.logto.io/end-user-flows/mfa/webauthn>
980. Logto docs: Passkey sign-in: <https://docs.logto.io/end-user-flows/sign-up-and-sign-in/passkey-sign-in>
981. Logto core CHANGELOG 1.38.0: support passkey sign-in authentication method: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L721>
982. Logto v1.45.0 source: sign-in methods (password, verificationCode): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/foundations/jsonb-types/sign-in-experience.ts#L133-L142>
983. Logto docs: Email verification for MFA: <https://docs.logto.io/end-user-flows/mfa/email-mfa>
984. Logto docs: SMS verification for MFA: <https://docs.logto.io/end-user-flows/mfa/sms-mfa>
985. Logto docs: Backup codes: <https://docs.logto.io/end-user-flows/mfa/backup-codes>
986. Logto docs: Configure MFA (optional, adaptive, mandatory, organization): <https://docs.logto.io/end-user-flows/mfa/configure-mfa>
987. Logto v1.45.0 schema: organizations.is_mfa_required: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/organizations.sql#L16>
988. Logto v1.45.0 source: adaptive MFA signals from edge-injected headers: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/utils/injected-header-mapping.ts#L12-L19>
989. Logto v1.45.0 source: defaultSentinelPolicy: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/consts/sentinel.ts#L9-L12>
990. Logto v1.45.0 source: BasicSentinel lockout decision: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/sentinel/basic-sentinel.ts#L154-L199>
991. Logto v1.45.0 source: lockout target is the hashed normalized identifier: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/routes/experience/classes/libraries/sentinel-guard.ts#L174-L178>
992. Logto docs: Identifier lockout: <https://docs.logto.io/security/identifier-lockout>
993. Logto v1.45.0 source: defaultMessageRateLimitPolicy: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/consts/message-rate-limit.ts#L42-L45>
994. Logto docs: Send rate limiting: <https://docs.logto.io/security/send-rate-limit>
995. Logto docs: Logto Cloud system limit, rate limit: <https://docs.logto.io/logto-cloud/system-limit#rate-limit>
996. Logto v1.45.0 source: password policy guard and defaults: <https://github.com/logto-io/logto/blob/v1.45.0/packages/toolkit/core-kit/src/password-policy.ts#L43-L63>
997. Logto v1.45.0 source: Have I Been Pwned range check: <https://github.com/logto-io/logto/blob/v1.45.0/packages/toolkit/core-kit/src/password-policy.ts#L304-L321>
998. Logto docs: Password policy: <https://docs.logto.io/security/password-policy>
999. Logto v1.45.0 source: CAPTCHA provider types: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/foundations/jsonb-types/captcha.ts#L3-L7>
1000. Logto docs: CAPTCHA bot protection: <https://docs.logto.io/security/captcha>
1001. Logto core CHANGELOG 1.44.0: support Cap as a self-hosted CAPTCHA provider: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L35>
1002. Logto v1.45.0 source: Argon2i password hashing parameters: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/workers/tasks/argon2i.ts#L12-L21>
1003. Logto v1.45.0 source: supported password hash verification methods: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/libraries/user-password-verification.ts#L54-L80>
1004. Logto v1.45.0 source: migrate legacy hashes to Argon2i on sign-in: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/libraries/user.ts#L216-L224>
1005. Logto docs: Audit logs: <https://docs.logto.io/developers/audit-logs>
1006. Logto v1.45.0 schema: logs table: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/tables/logs.sql#L3-L11>
1007. Logto v1.45.0 source: Console MFA requirement needs mandatoryMfa license grant: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/routes-me/tenant.ts#L99-L122>
1008. Logto v1.45.0 alteration: enable optional MFA for admin tenant: <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/alterations/1.36.0-1768464306-enable-mfa-for-admin-tenant.ts#L7-L18>
1009. Logto v1.45.0 source: admin tenant account center (mfa editable): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/seeds/account-center.ts#L19-L35>
1010. Logto v1.45.0 source: admin tenant sign-in experience seed (MFA factors, NoPrompt): <https://github.com/logto-io/logto/blob/v1.45.0/packages/schemas/src/seeds/sign-in-experience.ts#L83-L111>
1011. Logto v1.45.0 GitHub release notes: <https://github.com/logto-io/logto/releases/tag/v1.45.0>
1012. Logto docs: Get started with OSS (requirements, hardware): <https://docs.logto.io/logto-oss/get-started-with-oss>
1013. logto-io/logto issue #1726: maintainer, configs in database, HA ready: <https://github.com/logto-io/logto/issues/1726#issuecomment-1517413983>
1014. Logto docs: Central cache (Redis): <https://docs.logto.io/logto-oss/central-cache>
1015. Logto docs: Deployment and configuration (multiple instances, Kubernetes example): <https://docs.logto.io/logto-oss/deployment-and-configuration>
1016. Logto docs: Upgrading OSS version (replicas, alterations): <https://docs.logto.io/logto-oss/upgrading-oss-version>
1017. Logto v1.45.0 source: Application Insights only when connection string set: <https://github.com/logto-io/logto/blob/v1.45.0/packages/app-insights/src/node.ts#L67>
1018. Logto v1.45.0 source: /status health route: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/routes/status.ts#L17-L18>
1019. Logto v1.45.0 OpenAPI: health check description: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/routes/status.openapi.json#L11-L12>
1020. logto-io/logto PR #4242: add helm charts (closed, not merged): <https://github.com/logto-io/logto/pull/4242>
1021. Logto v1.45.0 LICENSE (Mozilla Public License 2.0): <https://github.com/logto-io/logto/blob/v1.45.0/LICENSE#L1>
1022. Logto v1.45.0 packages/core/package.json (author Silverhand Inc.): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/package.json#L6>
1023. Logto v1.45.0 vendored test helper license (MIT): <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/src/test-utils/jest-koa-mocks/LICENSE>
1024. Logto core CHANGELOG 1.45.0: license-based entitlements for self-hosted deployments: <https://github.com/logto-io/logto/blob/v1.45.0/packages/core/CHANGELOG.md?plain=1#L7-L13>

### Dex v2.46.1

1025. Dex README at v2.46.1: OIDC identity service, ID tokens signed by dex: <https://github.com/dexidp/dex/blob/v2.46.1/README.md#L11-L17>
1026. Dex source: discovery document construction: <https://github.com/dexidp/dex/blob/v2.46.1/server/discovery/discovery.go#L133-L177>
1027. Dex docs: OpenID Connect Provider Certification: <https://dexidp.io/docs/development/oidc-certification/>
1028. Dex source: default oauth2.grantTypes when unset: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L729-L741>
1029. Dex source: supportedTypes (grant/response type resolution): <https://github.com/dexidp/dex/blob/v2.46.1/server/config.go#L230-L272>
1030. Dex source: feature flags (client credentials, sessions): <https://github.com/dexidp/dex/blob/v2.46.1/pkg/featureflags/set.go#L21-L29>
1031. Dex source: client_credentials grant rejects public clients: <https://github.com/dexidp/dex/blob/v2.46.1/server/grants/clientcredentials.go#L52-L56>
1032. Dex source: token endpoint registers only supported grants: <https://github.com/dexidp/dex/blob/v2.46.1/server/grants/grants.go#L176-L190>
1033. Dex release notes v2.46.0: <https://github.com/dexidp/dex/releases/tag/v2.46.0>
1034. Dex docs: OAuth2 configuration, configurable grants: <https://dexidp.io/docs/configuration/oauth2/>
1035. Dex source: device authorization routes: <https://github.com/dexidp/dex/blob/v2.46.1/server/device/device.go#L59-L64>
1036. Dex release notes v2.25.0 (device authorization grant): <https://github.com/dexidp/dex/releases/tag/v2.25.0>
1037. Dex source: RFC 8693 token exchange grant: <https://github.com/dexidp/dex/blob/v2.46.1/server/grants/tokenexchange.go#L45-L64>
1038. Dex source: GitLab connector TokenIdentity (token exchange): <https://github.com/dexidp/dex/blob/v2.46.1/connector/gitlab/gitlab.go#L287-L295>
1039. Dex docs: Machine authentication to Dex (token exchange guide): <https://dexidp.io/docs/guides/token-exchange/>
1040. Dex release notes v2.38.0 (RFC 8693 token exchange): <https://github.com/dexidp/dex/releases/tag/v2.38.0>
1041. Dex DEP 4600: ID-JAG (proposal): <https://github.com/dexidp/dex/blob/v2.46.1/docs/enhancements/id-jag-2026-03-02%234600.md>
1042. Dex source: server.mount, every HTTP route handler: <https://github.com/dexidp/dex/blob/v2.46.1/server/server.go#L228-L343>
1043. Dex README at v2.46.1: connectors table: <https://github.com/dexidp/dex/blob/v2.46.1/README.md#L67-L85>
1044. Dex website home page: How Dex compares, CNCF Sandbox Project: <https://dexidp.io/>
1045. Dex source: built-in connector types: <https://github.com/dexidp/dex/blob/v2.46.1/server/connector.go#L26-L46>
1046. Dex docs: Authentication through LDAP: <https://dexidp.io/docs/connectors/ldap/>
1047. Dex source: LDAP connector optional Kerberos (SPNEGO) config: <https://github.com/dexidp/dex/blob/v2.46.1/connector/ldap/ldap.go#L128-L129>
1048. Dex docs: The Dex gRPC API: <https://dexidp.io/docs/configuration/api/>
1049. Dex source: introspection handler: <https://github.com/dexidp/dex/blob/v2.46.1/server/introspection/introspection.go#L353-L392>
1050. Dex test: introspection request sent without client credentials: <https://github.com/dexidp/dex/blob/v2.46.1/server/server_introspection_test.go#L228-L246>
1051. Dex source: refresh token reuse check: <https://github.com/dexidp/dex/blob/v2.46.1/server/tokens/refresh_lookup.go#L52-L62>
1052. Dex release notes v2.40.0 (introspect endpoint): <https://github.com/dexidp/dex/releases/tag/v2.40.0>
1053. Dex source: discovery document fields: <https://github.com/dexidp/dex/blob/v2.46.1/server/discovery/discovery.go#L52-L74>
1054. Dex gRPC API: ListRefresh/RevokeRefresh: <https://github.com/dexidp/dex/blob/v2.46.1/api/v2/api.proto#L569-L574>
1055. Dex issue #1778: revocation_endpoint for tokens (open): <https://github.com/dexidp/dex/issues/1778>
1056. Dex source: SignAccessToken mints a JWT via SignIDToken: <https://github.com/dexidp/dex/blob/v2.46.1/server/tokens/issuer.go#L86-L96>
1057. Dex source: idTokens expiry default 24h: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L314-L323>
1058. Dex source: local signer algorithm RS256 or ES256: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/config.go#L577-L586>
1059. Dex source: refresh token rotation/expiry strategy: <https://github.com/dexidp/dex/blob/v2.46.1/server/tokens/refresh_strategy.go#L36-L107>
1060. Dex source: refresh token rotation (ObsoleteToken): <https://github.com/dexidp/dex/blob/v2.46.1/server/tokens/refresh_store.go#L180-L188>
1061. Dex docs: Tokens, expiration and rotation settings: <https://dexidp.io/docs/configuration/tokens/>
1062. Dex config.yaml.dist: grpc and expiry blocks commented out: <https://github.com/dexidp/dex/blob/v2.46.1/config.yaml.dist#L78-L96>
1063. Dex source: logout routes mounted only with sessions: <https://github.com/dexidp/dex/blob/v2.46.1/server/logout/logout.go#L53-L61>
1064. Dex source: session config only when DEX_SESSIONS_ENABLED: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L429-L440>
1065. Dex source: back-channel logout notifier: <https://github.com/dexidp/dex/blob/v2.46.1/server/backchannel/backchannel.go#L25-L35>
1066. Dex DEP: Auth Sessions, Future Improvements (front-channel logout): <https://github.com/dexidp/dex/blob/v2.46.1/docs/enhancements/auth-sessions-2026-02-18.md#L1445-L1467>
1067. Dex issue #4755: Support Pushed Authorization Request (open): <https://github.com/dexidp/dex/issues/4755>
1068. Dex issue #2872: Support DPoP (open): <https://github.com/dexidp/dex/issues/2872>
1069. Dex example app README: gRPC API page: <https://github.com/dexidp/dex/blob/v2.46.1/examples/example-app/README.md#L74-L89>
1070. Dex source: gRPC API server, warning when no client CA: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L600-L622>
1071. Dex docs: builtin (local) connector, creating users: <https://dexidp.io/docs/connectors/local/>
1072. Dex source: list of HTML templates: <https://github.com/dexidp/dex/blob/v2.46.1/server/templates/templates.go#L21-L31>
1073. Dex source: storage.Claims (fixed claim set): <https://github.com/dexidp/dex/blob/v2.46.1/storage/storage.go#L263-L272>
1074. Dex source: storage.Password (local users, groups): <https://github.com/dexidp/dex/blob/v2.46.1/storage/storage.go#L566-L602>
1075. Dex config.yaml.dist: single issuer: <https://github.com/dexidp/dex/blob/v2.46.1/config.yaml.dist#L1-L4>
1076. Dex source: server.Config (one Issuer, one Storage): <https://github.com/dexidp/dex/blob/v2.46.1/server/config.go#L29-L33>
1077. Dex source: IDTokenClaims: <https://github.com/dexidp/dex/blob/v2.46.1/server/tokens/claims.go#L62-L91>
1078. Dex config.yaml.dist: staticClients, connectors, staticPasswords: <https://github.com/dexidp/dex/blob/v2.46.1/config.yaml.dist#L142-L223>
1079. dexidp GitHub org repositories (dex, website, helm-charts, .project): <https://github.com/orgs/dexidp/repositories>
1080. Dex source: validateMFA (requires sessions; TOTP/WebAuthn only): <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/config.go#L151-L193>
1081. Dex source: TOTP parameters and single-use check: <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/totp.go#L20-L44>
1082. Dex example config: mfa authenticators: <https://github.com/dexidp/dex/blob/v2.46.1/examples/config-dev.yaml#L184-L212>
1083. Dex source: MFA routes mounted only with authenticators: <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/handler.go#L257-L271>
1084. Dex source: MFA steps require a logged-in auth request: <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/handler.go#L54-L73>
1085. Dex source: WebAuthn login ceremony for the known user: <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/webauthn.go#L214-L228>
1086. Dex source: WebAuthnConfig fields: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/config.go#L747-L778>
1087. Dex source: buildMFAProviders WebAuthn arguments: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L939-L952>
1088. Dex source: MFA step in the /auth dispatcher: <https://github.com/dexidp/dex/blob/v2.46.1/server/authflow/dispatch.go#L63-L79>
1089. Dex gRPC API: ResetMFA: <https://github.com/dexidp/dex/blob/v2.46.1/api/v2/api.proto#L594-L595>
1090. Dex source: chainForClient (client mfaChain, default chain, connector type): <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/handler.go#L102-L133>
1091. Dex source: Client.MFAChain: <https://github.com/dexidp/dex/blob/v2.46.1/storage/storage.go#L206-L208>
1092. Dex source: password login POST handler: <https://github.com/dexidp/dex/blob/v2.46.1/server/authflow/password.go#L98-L115>
1093. Dex source: BlockedUntil check at login: <https://github.com/dexidp/dex/blob/v2.46.1/server/authflow/finalize.go#L21-L36>
1094. Dex PR #4884 (maintainer): enforce UserIdentity.BlockedUntil at login: <https://github.com/dexidp/dex/pull/4884>
1095. Dex issue #3509: brute force prevention (open): <https://github.com/dexidp/dex/issues/3509>
1096. Dex source: TODO, TOTP endpoint lacks rate limiting: <https://github.com/dexidp/dex/blob/v2.46.1/server/mfa/totp.go#L162-L167>
1097. Dex issue #1970: rate-limit by IP for critical endpoints (open, maintainer discussion): <https://github.com/dexidp/dex/issues/1970>
1098. Dex gRPC API: Password message takes a hash, no plaintext: <https://github.com/dexidp/dex/blob/v2.46.1/api/v2/api.proto#L114-L123>
1099. Dex source: bcrypt cost bounds: <https://github.com/dexidp/dex/blob/v2.46.1/server/passwords/passwords.go#L12-L37>
1100. Dex source: local connector bcrypt compare and cost check: <https://github.com/dexidp/dex/blob/v2.46.1/server/connectors/password.go#L51-L58>
1101. Dex source: Password.Hash bcrypt, min cost 10: <https://github.com/dexidp/dex/blob/v2.46.1/storage/storage.go#L577-L578>
1102. Dex source: login successful log line: <https://github.com/dexidp/dex/blob/v2.46.1/server/authflow/finalize.go#L66-L70>
1103. Dex source: CreateClient logs only on error: <https://github.com/dexidp/dex/blob/v2.46.1/server/apiserver/clients.go#L66-L75>
1104. Dex source: storage types: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/config.go#L447-L454>
1105. Dex docs: Storage: <https://dexidp.io/docs/configuration/storage/>
1106. Dex source: key rotation with multiple instances: <https://github.com/dexidp/dex/blob/v2.46.1/server/signer/rotation.go#L129-L138>
1107. Dex source: telemetry router (/metrics, /healthz\*) and listener: <https://github.com/dexidp/dex/blob/v2.46.1/cmd/dex/serve.go#L458-L515>
1108. Dex config.yaml.dist: telemetry commented out: <https://github.com/dexidp/dex/blob/v2.46.1/config.yaml.dist#L68-L70>
1109. Dex config.docker.yaml (image default): telemetry only if DEX_TELEMETRY_HTTP set: <https://github.com/dexidp/dex/blob/v2.46.1/config.docker.yaml#L18-L21>
1110. Dex Dockerfile: image default config config.docker.yaml: <https://github.com/dexidp/dex/blob/v2.46.1/Dockerfile#L40-L85>
1111. Dex Helm chart deployment: telemetry addr and probes: <https://github.com/dexidp/helm-charts/blob/bafe9258e234a59b048b0bddfd78b5b7e5619c40/charts/dex/templates/deployment.yaml#L79-L118>
1112. Dex source: /healthz on main HTTP router: <https://github.com/dexidp/dex/blob/v2.46.1/server/server.go#L332-L338>
1113. Dex Helm chart Chart.yaml (version 0.26.0, appVersion 2.46.0): <https://github.com/dexidp/helm-charts/blob/bafe9258e234a59b048b0bddfd78b5b7e5619c40/charts/dex/Chart.yaml>
1114. Dex Helm chart values: resources default: <https://github.com/dexidp/helm-charts/blob/bafe9258e234a59b048b0bddfd78b5b7e5619c40/charts/dex/values.yaml#L318-L331>
1115. Dex LICENSE at v2.46.1: <https://github.com/dexidp/dex/blob/v2.46.1/LICENSE>
1116. Dex README: License section: <https://github.com/dexidp/dex/blob/v2.46.1/README.md#L122-L124>
1117. Dex MAINTAINERS.md at v2.46.1: <https://github.com/dexidp/dex/blob/v2.46.1/MAINTAINERS.md#L1-L8>

### Kanidm 1.11.2

1118. Kanidm book @v1.11.2: Supported Features, OAuth2 / OpenID Connect: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L41-L58>
1119. Kanidm source @v1.11.2: oauth2.rs OIDC discovery document builder: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L3133-L3236>
1120. Kanidm source @v1.11.2: oauth2.rs PKCE enabled unless explicitly disabled: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L730-L740>
1121. Kanidm source @v1.11.2: oauth2.rs ES256 signing unless legacy crypto enabled: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L917-L940>
1122. Kanidm book @v1.11.2: OAuth2, client requirements (PKCE, ES256, RFC 9068): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/integrations/oauth2.md?plain=1#L20-L31>
1123. Kanidm source @v1.11.2: oauth2.rs token endpoint grant dispatch: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1191-L1305>
1124. Kanidm source @v1.11.2: oauth2.rs client credentials grant (JWE token): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1864-L1970>
1125. Kanidm source @v1.11.2: kanidmd_lib cargo features (dev-oauth2-device-flow): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/Cargo.toml#L20-L25>
1126. Kanidm source @v1.11.2: core https oauth2.rs route setup: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/oauth2.rs#L764-L860>
1127. Kanidm source @v1.11.2: oauth2.rs device flow stubs: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1308-L1371>
1128. Kanidm source @v1.11.2: Makefile KANIDM_FEATURES default empty: <https://github.com/kanidm/kanidm/blob/v1.11.2/Makefile#L16>
1129. Kanidm book @v1.11.2: Service Accounts, API tokens with OIDC Token Exchange (RFC 8693): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/service_accounts.md?plain=1#L74-L103>
1130. Kanidm source @v1.11.2: oauth2.rs token exchange (service account): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1745-L1862>
1131. Kanidm release notes @v1.11.2: 1.9.0: <https://github.com/kanidm/kanidm/blob/v1.11.2/RELEASE_NOTES.md?plain=1#L111-L160>
1132. kanidm issue #2025: SAML (open): <https://github.com/kanidm/kanidm/issues/2025>
1133. kanidm issue #2025 comment by maintainer yaleman (2025-11-27): not scheduled: <https://github.com/kanidm/kanidm/issues/2025#issuecomment-3586163669>
1134. kanidm issue #2025 comment by maintainer Firstyear: SAML security risks: <https://github.com/kanidm/kanidm/issues/2025#issuecomment-1692669023>
1135. Kanidm book @v1.11.2: LDAP integration (read-only, LDAPS only, config): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/integrations/ldap.md?plain=1#L1-L85>
1136. Kanidm source @v1.11.2: config.rs ldapbindaddress (unset = disabled): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/config.rs#L310-L319>
1137. Kanidm book @v1.11.2: Supported Features, LDAP (read-only): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L31-L39>
1138. Kanidm example server_container.toml @v1.11.2: ldapbindaddress defaults to disabled: <https://github.com/kanidm/kanidm/blob/v1.11.2/examples/server_container.toml#L11-L16>
1139. Kanidm book @v1.11.2: Synchronisation concepts: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/sync/concepts.md?plain=1#L1-L30>
1140. Kanidm book @v1.11.2: LDAP sync tool (RFC 4533): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/sync/ldap.md?plain=1#L1-L10>
1141. Kanidm book @v1.11.2: FreeIPA sync tool: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/sync/freeipa.md?plain=1#L1-L10>
1142. Kanidm book @v1.11.2: Supported Features, Data Import (SCIM note): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L19-L28>
1143. Kanidm source @v1.11.2: SCIM-style API routes: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/v1_scim.rs#L265-L1030>
1144. Kanidm book @v1.11.2: RADIUS, deploying the RADIUS container: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/integrations/radius.md?plain=1#L95-L141>
1145. Kanidm book @v1.11.2: Supported Features, RADIUS: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L60-L63>
1146. Kanidm release notes @v1.11.2: 1.11.0: <https://github.com/kanidm/kanidm/blob/v1.11.2/RELEASE_NOTES.md?plain=1#L17-L57>
1147. Kanidm book @v1.11.2: Kubernetes Ingress example (uses OAuth2 Proxy): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/examples/kubernetes_ingress.md?plain=1#L44-L50>
1148. Kanidm source @v1.11.2: web UI routes: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/views/mod.rs#L50-L180>
1149. Kanidm source @v1.11.2: oauth2.rs token introspection (no caller auth): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L2732-L2750>
1150. Kanidm release notes @v1.11.2: 1.10.0: <https://github.com/kanidm/kanidm/blob/v1.11.2/RELEASE_NOTES.md?plain=1#L59-L110>
1151. Kanidm source @v1.11.2: oauth2.rs token revocation: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1058-L1185>
1152. Kanidm source @v1.11.2: oauth2.rs access/ID/refresh token generation: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1971-L2190>
1153. Kanidm source @v1.11.2: oauth2.rs refresh grant with reuse detection: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2.rs#L1603-L1740>
1154. Kanidm book @v1.11.2: design doc, OAuth2 refresh tokens (NIB / reuse): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/developers/designs/oauth2_refresh_tokens.md?plain=1#L72-L124>
1155. Kanidm source @v1.11.2: proto OidcDiscoveryResponse struct: <https://github.com/kanidm/kanidm/blob/v1.11.2/proto/src/oauth2.rs#L620>
1156. kanidm issue #1997: add end_session_endpoint to discovery (open): <https://github.com/kanidm/kanidm/issues/1997>
1157. kanidm issue #3752 comment by maintainer yaleman: end_session not exposed yet: <https://github.com/kanidm/kanidm/issues/3752#issuecomment-3124402173>
1158. kanidm issue #2412 comment by maintainer Firstyear: backchannel logout not supported: <https://github.com/kanidm/kanidm/issues/2412#issuecomment-1876240710>
1159. kanidm issue #4240: OAuth2 Global Logout (open): <https://github.com/kanidm/kanidm/issues/4240>
1160. Kanidm source @v1.11.2: proto AccessTokenType enum: <https://github.com/kanidm/kanidm/blob/v1.11.2/proto/src/oauth2.rs#L289-L298>
1161. Kanidm source @v1.11.2: web UI admin routes: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/views/admin/mod.rs#L9-L36>
1162. Kanidm source @v1.11.2: navbar Admin link gated by ExperimentalFeatures: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/templates/navbar.html#L34-L39>
1163. Kanidm source @v1.11.2: idm_ui_enable_experimental_features group: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/groups.rs#L418-L429>
1164. Kanidm README @v1.11.2: admin functionality primarily via CLI: <https://github.com/kanidm/kanidm/blob/v1.11.2/README.md?plain=1#L95-L96>
1165. Kanidm book @v1.11.2: REST interface (OpenAPI, Swagger UI): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/developers/designs/rest_interface.md?plain=1#L1-L14>
1166. Kanidm book @v1.11.2: Service Accounts, API tokens with the HTTPS/REST API: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/service_accounts.md?plain=1#L66-L72>
1167. Kanidm book @v1.11.2: People accounts, creation by idm_people_admins: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/people_accounts.md?plain=1#L9-L15>
1168. Kanidm book @v1.11.2: Account recovery (off by default, proof-of-work): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/authentication_and_credentials.md?plain=1#L137-L152>
1169. Kanidm book @v1.11.2: Outgoing email (kanidm-mail-sender): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/email_setup.md?plain=1#L8-L15>
1170. Kanidm source @v1.11.2: account recovery domain flag defaults to false: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/server/mod.rs#L2572-L2574>
1171. Kanidm book @v1.11.2: Groups, nested groups: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/groups.md?plain=1#L22-L47>
1172. Kanidm book @v1.11.2: Supported Features, Authorisation (RBAC): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L3-L8>
1173. Kanidm book @v1.11.2: OAuth2, scope relationships (group scope maps): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/integrations/oauth2.md?plain=1#L287-L315>
1174. Kanidm example server_container.toml @v1.11.2: single domain setting: <https://github.com/kanidm/kanidm/blob/v1.11.2/examples/server_container.toml#L66-L82>
1175. Kanidm book @v1.11.2: Choosing a domain name, separate instances: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/choosing_a_domain_name.md?plain=1#L343-L355>
1176. Kanidm source @v1.11.2: upstream OAuth2 client provider (in development): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/oauth2_client.rs#L11-L29>
1177. Kanidm source @v1.11.2: OAuth2Client (authentication source) schema class: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/schema.rs#L1368-L1386>
1178. kanidm issue #4015 comment by maintainer yaleman: upstream OIDC federation very early in development: <https://github.com/kanidm/kanidm/issues/4015#issuecomment-3650076374>
1179. kanidm issue #4257 comment by maintainer yaleman: OAuth federation planned: <https://github.com/kanidm/kanidm/issues/4257#issuecomment-4217709412>
1180. kanidm issue #3493 comment by maintainer Firstyear: custom fields supported but not advertised: <https://github.com/kanidm/kanidm/issues/3493#issuecomment-2719514886>
1181. Kanidm source @v1.11.2: schema write access control for idm_schema_admins: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/access.rs#L227-L238>
1182. Kanidm source @v1.11.2: CLI schema commands (list/search only): <https://github.com/kanidm/kanidm/blob/v1.11.2/tools/cli/src/opt/kanidm.rs#L1438-L1470>
1183. Kanidm book @v1.11.2: Entry management (HJSON migrations): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/entry_management.md?plain=1#L1-L60>
1184. Kanidm example migration @v1.11.2: OAuth2 client as HJSON: <https://github.com/kanidm/kanidm/blob/v1.11.2/examples/migrations/10-oauth2.hjson>
1185. Kanidm source @v1.11.2: TOTP generate_secure defaults: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/credential/totp.rs#L173-L177>
1186. Kanidm source @v1.11.2: TOTP enrolment and SHA-1 fallback: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/credupdatesession.rs#L2147-L2310>
1187. Kanidm book @v1.11.2: Types of credentials (passkeys, password+TOTP): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/authentication_and_credentials.md?plain=1#L6-L35>
1188. Kanidm source @v1.11.2: security keys are deprecated message: <https://github.com/kanidm/kanidm/blob/v1.11.2/proto/src/internal/credupdate.rs#L276-L287>
1189. Kanidm source @v1.11.2: legacy password + security key auth handler: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/authsession/mod.rs#L355-L385>
1190. Kanidm book @v1.11.2: Account policy, default policy and credential type minimum: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/account_policy.md?plain=1#L11-L32>
1191. Kanidm source @v1.11.2: AuthAllowed enum (supported login mechanisms): <https://github.com/kanidm/kanidm/blob/v1.11.2/proto/src/v1/auth.rs#L164-L174>
1192. Kanidm source @v1.11.2: backup code generation (8 codes): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/utils.rs#L49-L51>
1193. Kanidm source @v1.11.2: backup code enrolment: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/credupdatesession.rs#L2350-L2396>
1194. Kanidm source @v1.11.2: CLI credential update 'backup codes': <https://github.com/kanidm/kanidm/blob/v1.11.2/tools/cli/src/cli/person.rs#L817>
1195. Kanidm source @v1.11.2: idm_all_persons default account policy (MFA): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/groups.rs#L375-L396>
1196. Kanidm source @v1.11.2: credential commit enforces credential type minimum: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/credupdatesession.rs#L210-L232>
1197. Kanidm source @v1.11.2: account policy not fully enforced at auth (TODO): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/authsession/mod.rs#L1159-L1165>
1198. Kanidm source @v1.11.2: credential soft-lock policies: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/credential/softlock.rs#L64-L151>
1199. Kanidm source @v1.11.2: in-memory soft-lock map keyed by credential UUID: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/server.rs#L1242-L1265>
1200. Kanidm source @v1.11.2: soft-lock policy per credential type: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/credential/mod.rs#L789-L812>
1201. Kanidm book @v1.11.2: design doc, account policy and lockouts (rate limiting): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/developers/designs/account_policy.rst?plain=1#L42-L84>
1202. Kanidm source @v1.11.2: HTTPS middleware stack: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/mod.rs#L359-L399>
1203. Kanidm source @v1.11.2: check_password_quality: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/credupdatesession.rs#L1879-L2049>
1204. Kanidm source @v1.11.2: min length raised to 15 when MFA not required: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/accountpolicy.rs#L177-L183>
1205. Kanidm source @v1.11.2: password length constants: <https://github.com/kanidm/kanidm/blob/v1.11.2/libs/crypto/src/lib.rs#L38-L51>
1206. Kanidm source @v1.11.2: default system config password badlist: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/system_config.rs#L69-L720>
1207. Kanidm book @v1.11.2: Account policy, password minimum length: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/account_policy.md?plain=1#L120-L131>
1208. Kanidm book @v1.11.2: Account policy, password quality, badlist, rotation: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/account_policy.md?plain=1#L229-L274>
1209. Kanidm source @v1.11.2: HMAC-SHA256 proof-of-work challenge: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/views/csrf.rs#L14-L141>
1210. Kanidm source @v1.11.2: account recovery form (only PoW user): <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/views/recover.rs#L45-L119>
1211. Kanidm source @v1.11.2: 10 ms hash time target: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/server.rs#L152-L158>
1212. Kanidm source @v1.11.2: Argon2id parameter bounds: <https://github.com/kanidm/kanidm/blob/v1.11.2/libs/crypto/src/lib.rs#L72-L86>
1213. Kanidm source @v1.11.2: CryptoPolicy::time_target Argon2id auto-tuning: <https://github.com/kanidm/kanidm/blob/v1.11.2/libs/crypto/src/lib.rs#L193-L317>
1214. Kanidm source @v1.11.2: legacy hash formats flagged for upgrade: <https://github.com/kanidm/kanidm/blob/v1.11.2/libs/crypto/src/lib.rs#L1211-L1246>
1215. Kanidm book @v1.11.2: Supported Features, Cryptography (Argon2ID): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/supported_features.md?plain=1#L9-L16>
1216. Kanidm source @v1.11.2: AuditEvent enum: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/audit.rs#L23-L32>
1217. Kanidm source @v1.11.2: audit events written to the log: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/lib.rs#L1257-L1285>
1218. Kanidm source @v1.11.2: tagged security/admin log macros: <https://github.com/kanidm/kanidm/blob/v1.11.2/libs/sketching/src/macros.rs#L44-L91>
1219. Kanidm book @v1.11.2: Accounts intro, break-glass admin accounts: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/accounts/intro.md?plain=1#L29-L65>
1220. Kanidm source @v1.11.2: builtin admin and idm_admin service accounts: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/migration_data/dl15/accounts.rs#L6-L24>
1221. Kanidm source @v1.11.2: recover_account sets generated password: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/lib/src/idm/server.rs#L2022-L2054>
1222. Kanidm book @v1.11.2: FAQ, changing the database backend from SQLite: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/frequently_asked_questions.md?plain=1#L117-L131>
1223. Kanidm book @v1.11.2: Replication introduction: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/repl/readme.md?plain=1#L5-L17>
1224. Kanidm book @v1.11.2: Support policy (replication max 2 nodes): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/support.md?plain=1#L80-L96>
1225. Kanidm source @v1.11.2: config.rs replication and otel_grpc_endpoint docs: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/config.rs#L345-L349>
1226. Kanidm book @v1.11.2: Monitoring the platform (/status, OpenTelemetry): <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/monitoring_the_platform.md?plain=1#L1-L39>
1227. Kanidm source @v1.11.2: KANIDM_OTEL_GRPC_ENDPOINT env option: <https://github.com/kanidm/kanidm/blob/v1.11.2/proto/src/cli.rs#L13-L18>
1228. Kanidm source @v1.11.2: /status handler: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/generic.rs#L13-L35>
1229. Kanidm source @v1.11.2: /status route: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/core/src/https/mod.rs#L375>
1230. Kanidm source @v1.11.2: server Dockerfile HEALTHCHECK: <https://github.com/kanidm/kanidm/blob/v1.11.2/server/Dockerfile#L102-L109>
1231. kanidm issue #282: k8s support (open): <https://github.com/kanidm/kanidm/issues/282>
1232. Kanidm book @v1.11.2: Preparing for deployment, system requirements: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/preparing_for_your_deployment.md?plain=1#L32-L57>
1233. Kanidm LICENSE.md @v1.11.2 (MPL-2.0): <https://github.com/kanidm/kanidm/blob/v1.11.2/LICENSE.md>
1234. Kanidm workspace Cargo.toml @v1.11.2 (authors, license): <https://github.com/kanidm/kanidm/blob/v1.11.2/Cargo.toml#L1-L12>
1235. Kanidm tools/orca/names-dataset LICENSE @v1.11.2 (MIT): <https://github.com/kanidm/kanidm/blob/v1.11.2/tools/orca/names-dataset/LICENSE>
1236. Kanidm book @v1.11.2: Support and release processes: <https://github.com/kanidm/kanidm/blob/v1.11.2/book/src/support.md?plain=1#L1-L12>
1237. Kanidm README @v1.11.2: supported features list: <https://github.com/kanidm/kanidm/blob/v1.11.2/README.md?plain=1#L19-L38>
1238. Kanidm CONTRIBUTORS.md @v1.11.2: <https://github.com/kanidm/kanidm/blob/v1.11.2/CONTRIBUTORS.md?plain=1#L1-L4>

### Pocket ID v2.19.1

1239. Pocket ID v2.19.1 source: OIDC discovery document (well_known_controller.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/controller/well_known_controller.go#L99-L129>
1240. Pocket ID v2.19.1 source: Fosite provider config and composed grant handlers (oidc/provider.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/provider.go#L38-L103>
1241. Pocket ID docs: Scopes and claims (custom claims, token formats and lifetimes): <https://pocket-id.org/docs/guides/scopes-and-claims>
1242. Pocket ID v2.19.1 source: grant types per client, client_credentials only for confidential clients (oidc/client.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/client.go#L50-L58>
1243. Pocket ID docs: APIs and permissions (client credentials): <https://pocket-id.org/docs/guides/apis>
1244. Pocket ID v1.11.0 release notes (client_credentials flow support): <https://github.com/pocket-id/pocket-id/releases/tag/v1.11.0>
1245. Pocket ID v2.19.1 source: OIDC/OAuth route registration (oidc/module.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/module.go#L150-L174>
1246. Pocket ID docs: Connect an app, Endpoints: <https://pocket-id.org/docs/setup/connect-an-app#endpoints>
1247. Pocket ID issue #1250: maintainer reply on SAML (closed as not planned): <https://github.com/pocket-id/pocket-id/issues/1250#issuecomment-3764177977>
1248. Pocket ID docs: Authentication proxies: <https://pocket-id.org/docs/guides/proxy-services>
1249. Pocket ID docs: Introduction: <https://pocket-id.org/docs/introduction>
1250. Pocket ID docs: LDAP: <https://pocket-id.org/docs/configuration/ldap>
1251. Pocket ID v2.19.1 source: application configuration defaults (appconfig/model.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/appconfig/model.go#L134-L191>
1252. Pocket ID v2.19.1 source: hourly LDAP sync interval (ldapsync/actor.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/ldapsync/actor.go#L24-L26>
1253. Pocket ID v2.19.1 source: LDAP sync binds only with the configured service account (ldapsync/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/ldapsync/service.go#L107>
1254. Pocket ID docs: SCIM provisioning: <https://pocket-id.org/docs/configuration/scim>
1255. Pocket ID v2.19.1 source: SCIM routes are admin config for outbound service providers (scimsync/module.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/scimsync/module.go#L53-L57>
1256. Pocket ID v2.0.0 release notes (SCIM provisioning): <https://github.com/pocket-id/pocket-id/releases/tag/v2.0.0>
1257. Pocket ID v2.19.1 source: token introspection handler and caller checks (oidc/introspection_handler.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/introspection_handler.go#L35-L115>
1258. Pocket ID v2.19.1 source: revoking an app authorization revokes its sessions (service/oidc_service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/service/oidc_service.go#L785-L800>
1259. Pocket ID v2.19.1 source: token strategies, JWT access tokens vs opaque codes and refresh tokens (oidc/strategy_provider.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/strategy_provider.go#L31-L41>
1260. Pocket ID v2.13.0 release notes (RFC 9068 compliant access tokens): <https://github.com/pocket-id/pocket-id/releases/tag/v2.13.0>
1261. Pocket ID v2.19.1 source: refresh token rotation with 1-minute grace period (oidc/store.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/store.go#L375-L419>
1262. pocket-id/fosite v1.4.3 (fork pinned in Pocket ID go.mod): refresh token reuse detection (handler/oauth2/flow_refresh.go): <https://github.com/pocket-id/fosite/blob/v1.4.3/handler/oauth2/flow_refresh.go#L54-L63>
1263. Pocket ID v2.17.0 release notes (OIDC back-channel logout, 1 min refresh token grace period): <https://github.com/pocket-id/pocket-id/releases/tag/v2.17.0>
1264. Pocket ID v2.19.1 source: RP-initiated logout service (oidc/end_session_service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/end_session_service.go#L36-L95>
1265. Pocket ID v2.19.1 source: end-session handler (oidc/end_session_handler.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/end_session_handler.go#L25-L46>
1266. Pocket ID v2.19.1 source: OIDC Back-Channel Logout service (backchannellogout/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/backchannellogout/service.go#L28-L35>
1267. Pocket ID v2.19.1 source: back-channel logout sent when a user is disabled (service/user_service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/service/user_service.go#L541-L544>
1268. Pocket ID v2.19.1 source: per-client PAR requirement and re-authentication (oidc/authorization_service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/authorization_service.go#L120-L160>
1269. Pocket ID v2.9.0 release notes (Pushed Authorization Requests, RFC 9126): <https://github.com/pocket-id/pocket-id/releases/tag/v2.9.0>
1270. Pocket ID v2.19.1 source: admin UI routes (frontend/src/routes/settings/admin): <https://github.com/pocket-id/pocket-id/tree/v2.19.1/frontend/src/routes/settings/admin>
1271. Pocket ID docs: User management (signup links, groups): <https://pocket-id.org/docs/setup/user-management>
1272. Pocket ID docs: REST API and API keys: <https://pocket-id.org/docs/api>
1273. Pocket ID v2.19.1 source: session and X-API-Key authentication (middleware/authenticator.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/middleware/authenticator.go#L19-L28>
1274. Pocket ID v2.19.1 source: API key validation, static key and SHA-256 lookup (apikey/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/apikey/service.go#L160-L170>
1275. Pocket ID docs: Environment variables: <https://pocket-id.org/docs/configuration/environment-variables>
1276. Pocket ID v2.19.1 source: self-signup gating (usersignup/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/usersignup/service.go#L55-L60>
1277. Pocket ID docs: Sign-in methods: <https://pocket-id.org/docs/guides/sign-in-methods>
1278. Pocket ID v2.19.1 source: user model without a password field (model/user.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/model/user.go#L13-L32>
1279. Pocket ID v2.19.1 source: admin flag stands in for roles (authz/scope.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/authz/scope.go#L140-L150>
1280. Pocket ID v2.19.1 source: federated JWT client assertions for client authentication (oidc/federated_client_auth.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/oidc/federated_client_auth.go#L91-L112>
1281. Pocket ID docs: OIDC client authentication (federated client credentials): <https://pocket-id.org/docs/guides/oidc-client-authentication>
1282. Pocket ID issue #1842: maintainer reply on full declarative (GitOps) configuration: <https://github.com/pocket-id/pocket-id/issues/1842#issuecomment-6372120787>
1283. Pocket ID issue #937: maintainer reply on TOTP (closed as not planned): <https://github.com/pocket-id/pocket-id/issues/937#issuecomment-3284689624>
1284. Pocket ID v2.19.1 source: discoverable passkey login (webauthn/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/webauthn/service.go#L230-L233>
1285. Pocket ID v2.19.1 source: passkey registration, resident key required (webauthn/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/webauthn/service.go#L95-L102>
1286. Pocket ID v2.19.1 source: login codes by email, gated by settings (onetimeaccess/service.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/onetimeaccess/service.go#L58-L89>
1287. Pocket ID docs: Account recovery: <https://pocket-id.org/docs/troubleshooting/account-recovery>
1288. Pocket ID v2.19.1 source: rate-limit policies and per-IP middleware (middleware/rate_limit.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/middleware/rate_limit.go#L49-L122>
1289. Pocket ID v2.19.1 source: route registration with the rate limits applied (bootstrap/router_bootstrap.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/bootstrap/router_bootstrap.go#L151-L205>
1290. Pocket ID v2.2.0 release notes (environment variable to disable built-in rate limiting): <https://github.com/pocket-id/pocket-id/releases/tag/v2.2.0>
1291. Pocket ID v2.19.1 source: client secret hash algorithms (model/oidc.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/model/oidc.go#L101-L111>
1292. Pocket ID v2.19.1 source: audit log event types (auditlogs/model.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/auditlogs/model.go#L30-L41>
1293. Pocket ID v2.19.1 source: audit log retention cleanup job (auditlogs/cleanup_job.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/auditlogs/cleanup_job.go#L57-L63>
1294. Pocket ID v2.19.1 source: environment variable defaults (common/env_config.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/common/env_config.go#L172-L194>
1295. Pocket ID v2.19.1 source: database provider selection (common/env_config.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/common/env_config.go#L294-L304>
1296. Pocket ID v2.19.1 source: actor cluster capped at a single replica without HA (bootstrap/actors_bootstrap.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/bootstrap/actors_bootstrap.go#L93-L99>
1297. Pocket ID v2.19.1 source: HAEnabled flag intentionally not bound to an env var (common/env_config.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/common/env_config.go#L139-L142>
1298. Pocket ID issue #1549: tracking issue for High Availability / horizontal scaling (open): <https://github.com/pocket-id/pocket-id/issues/1549>
1299. Pocket ID v2.19.1 source: metrics exporter defaults to none (bootstrap/observability_boostrap.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/bootstrap/observability_boostrap.go#L186-L192>
1300. Pocket ID v2.19.1 source: /healthz endpoint (controller/healthz_controller.go): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/backend/internal/controller/healthz_controller.go#L15-L32>
1301. Pocket ID docs: Container hardening, System requirements: <https://pocket-id.org/docs/advanced/hardening#system-requirements>
1302. Pocket ID docs: Installation (incl. community installation methods): <https://pocket-id.org/docs/setup/installation>
1303. Pocket ID issue #1331: maintainer reply on an official Helm chart: <https://github.com/pocket-id/pocket-id/issues/1331#issuecomment-3947103031>
1304. Pocket ID website: landing page feature list: <https://pocket-id.org/>
1305. Pocket ID v2.19.1: LICENSE (BSD 2-Clause): <https://github.com/pocket-id/pocket-id/blob/v2.19.1/LICENSE>
1306. Pocket ID docs: Sponsors (maintainers and GitHub Sponsors): <https://pocket-id.org/docs/helping-out/sponsors>
