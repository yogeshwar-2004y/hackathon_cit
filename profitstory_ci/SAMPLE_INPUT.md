# Sample input for ProfitStory CI scan

## Recommended: more reviews, less captcha

Use **fewer ASINs** (1 product + 1 competitor) so fewer requests are made → less likely to hit captcha. Use **high-review products** so when scraping works, you get real review data (and more PDP snippets).

| Field | Recommended value |
|-------|-------------------|
| **product_asin** | `B0CP54XBWN` (boAt Airdopes 91 – high reviews) |
| **competitor_asins** | `B0F7LY85KB` (boAt Rockerz 421 – one competitor only) |

This is the **default** in the UI and API. Only 2 ASINs = 2 product pages + 2 review-page attempts = lower captcha risk.

---

## Default scan (from UI or API)

| Field | Default value |
|-------|----------------|
| **product_asin** | `B0CP54XBWN` |
| **competitor_asins** | `B0F7LY85KB` |

---

## Sample inputs you can paste

### Option A – Recommended (1 product + 1 competitor, fewer requests)
```
product_asin: B0CP54XBWN
competitor_asins: B0F7LY85KB
```

### Option B – Same, different competitor
```
product_asin: B0CP54XBWN
competitor_asins: B0FC327SXQ
```

### Option C – Two competitors (slightly more requests)
```
product_asin: B0CP54XBWN
competitor_asins: B0F7LY85KB,B0FC327SXQ
```

### Option D – Different product (Sony headphone)
```
product_asin: B0863TXGM3
competitor_asins: B0F7LY85KB
```

### Option E – Books (often many reviews, sometimes less blocking)
```
product_asin: 0143429684
competitor_asins: 8172234988
```
(Use book ISBNs as ASINs on Amazon India if you want to try a different category.)

---

## API examples

**POST /scan** (form or query params):

```bash
# Default
curl -X POST "http://localhost:8000/scan"

# Custom product + competitors
curl -X POST "http://localhost:8000/scan?product_asin=B0CP54XBWN&competitor_asins=B0FC327SXQ,B0F7LY85KB"
```

**Form body (e.g. from frontend):**
- `product_asin`: one ASIN (e.g. `B0863TXGM3`)
- `competitor_asins`: comma-separated ASINs (no spaces or with spaces, both work)

**Response:**
```json
{ "job_id": "42d785ad", "status": "started" }
```

Then open the SSE stream for logs/results:
- `GET /job/{job_id}/stream` (EventSource)
- `GET /results/latest` for the latest run
- `GET /logs?limit=100` for backend log lines

---

## Good our product / Bad competitor (real input for signals)

Use this pairing to see **strong vulnerability signals**: our product has better reviews, competitor has more negative ones (quality issues, sound died, etc.).

| Field | Value |
|-------|--------|
| **product_asin** | `B0863TXGM3` (Sony WH-1000XM4 – premium, generally good reviews) |
| **competitor_asins** | `B0F7LY85KB` (boAt Rockerz 421 – budget; often more “sound died”, “one side stopped” type reviews) |

**Copy-paste:**
```
product_asin: B0863TXGM3
competitor_asins: B0F7LY85KB
```

**API:**
```bash
curl -X POST "http://localhost:8000/scan?product_asin=B0863TXGM3&competitor_asins=B0F7LY85KB"
```

The Detective node will compare sentiment and review content; you should see higher vulnerability / distress signals on the competitor and a clearer “our product vs weak competitor” picture.

---

## Quick copy-paste (for UI or API)

| Use case | product_asin | competitor_asins |
|----------|--------------|------------------|
| **Good us / Bad competitor (real)** | `B0863TXGM3` | `B0F7LY85KB` |
| **Recommended (fewer captcha)** | `B0CP54XBWN` | `B0F7LY85KB` |
| Same product, 2 competitors | `B0CP54XBWN` | `B0F7LY85KB,B0FC327SXQ` |
| Different product | `B0863TXGM3` | `B0F7LY85KB` |

**Why fewer ASINs helps:** Fewer requests per scan = less chance of captcha. High-review products (e.g. boAt Airdopes 91) often show review snippets on the product page, so you can still get real review text even if the dedicated reviews page is blocked.
