import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

export function HelpIndexPage() {
  const [topics, setTopics] = useState<
    { slug: string; title: string }[]
  >([]);

  useEffect(() => {
    apiGet<{ topics: { slug: string; title: string }[] }>("/help/topics").then(
      (r) => setTopics(r.topics)
    );
  }, []);

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Help</h1>
      <Card>
        <ul>
          {topics.map((t) => (
            <li key={t.slug}>
              <Link to={`/help/${t.slug}`}>{t.title}</Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
