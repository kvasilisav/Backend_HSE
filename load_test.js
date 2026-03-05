import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  stages: [
    { duration: "30s", target: 5 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    http_req_failed: ["rate<0.1"],
  },
};

export default function () {
  const predictPayload = JSON.stringify({
    seller_id: 1,
    is_verified_seller: false,
    item_id: 1,
    name: "Test",
    description: "A good item",
    category: 5,
    images_qty: 2,
  });

  let res = http.post(`${BASE}/predict`, predictPayload, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "predict status 200 or 503": (r) => r.status === 200 || r.status === 503 });

  res = http.get(`${BASE}/`);
  check(res, { "root status 200": (r) => r.status === 200 });

  res = http.get(`${BASE}/moderation_result/1`);
  check(res, {
    "moderation_result 200/404/503": (r) =>
      r.status === 200 || r.status === 404 || r.status === 503,
  });

  res = http.post(`${BASE}/predict`, "{}", {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "predict invalid 422": (r) => r.status === 422 });

  sleep(0.5);
}
