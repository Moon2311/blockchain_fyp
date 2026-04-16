import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

export function HelpTopicPage() {
  const { slug } = useParams();
  const [body, setBody] = useState<{ title: string; body: string } | null>(
    null
  );
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    apiGet<{ title: string; body: string }>(`/help/topics/${slug}`)
      .then(setBody)
      .catch((e) => setErr(String(e)));
  }, [slug]);

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!body) return <p className="muted">Loading…</p>;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <p>
        <Link to="/help">← Help</Link>
      </p>
      <h1>{body.title}</h1>
      <Card>
        <div
          className="help-html"
          dangerouslySetInnerHTML={{ __html: body.body }}
        />
      </Card>
    </div>
  );
}
