import { Suspense } from "react";
import RatingFlow from "./RatingFlow";

// The flow reads search params (lang, rater) on the client, so wrap in Suspense.
export default function RatePage() {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <RatingFlow />
    </Suspense>
  );
}
