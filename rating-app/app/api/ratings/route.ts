import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

// One rating row per rater × item. Upsert so a rater re-submitting an item
// updates rather than duplicates (matches the unique index in schema.sql).
export async function POST(req: Request) {
  try {
    const sql = getSql();
    const b = await req.json();
    if (!b?.task_id || !b?.rater_id || !b?.language) {
      return NextResponse.json({ ok: false, error: "missing task_id/rater_id/language" }, { status: 400 });
    }
    for (const k of ["fluency", "bias"] as const) {
      const v = b[k];
      if (!Number.isInteger(v) || v < 1 || v > 4) {
        return NextResponse.json({ ok: false, error: `${k} must be an integer 1-4` }, { status: 400 });
      }
    }
    // faithfulness is optional: bottom-up items have no English source to match,
    // so the rater never scores it. Validate only when a value is present.
    if (b.faithfulness != null) {
      if (!Number.isInteger(b.faithfulness) || b.faithfulness < 1 || b.faithfulness > 4) {
        return NextResponse.json({ ok: false, error: "faithfulness must be an integer 1-4" }, { status: 400 });
      }
    }

    await sql`
      insert into ratings (
        task_id, rater_id, rater_name, language, task_family,
        fluency, faithfulness, bias, unsure, comment,
        instructions_version, started_at, submitted_at
      ) values (
        ${b.task_id}, ${b.rater_id}, ${b.rater_name ?? null}, ${b.language}, ${b.task_family ?? null},
        ${b.fluency}, ${b.faithfulness ?? null}, ${b.bias}, ${b.unsure ?? false}, ${b.comment ?? null},
        ${b.instructions_version ?? "v1"}, ${b.started_at ?? null}, ${b.submitted_at ?? null}
      )
      on conflict (rater_id, task_id) do update set
        rater_name = excluded.rater_name,
        fluency = excluded.fluency,
        faithfulness = excluded.faithfulness,
        bias = excluded.bias,
        unsure = excluded.unsure,
        comment = excluded.comment,
        started_at = excluded.started_at,
        submitted_at = excluded.submitted_at,
        created_at = now()
    `;
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 });
  }
}
