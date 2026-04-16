import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiPostJson } from "../services/api";

export function CaseNewPage() {
  const nav = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await apiPostJson<{ case: { id: number } }>("/cases", {
        title: title.trim(),
        description: description.trim() || null,
      });
      nav(`/cases/${r.case.id}`);
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>New case</h1>
      <Card>
        <form onSubmit={onSubmit} className="stack">
          <label>
            Title *
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: "0.35rem", padding: "0.5rem" }}
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              style={{ display: "block", width: "100%", marginTop: "0.35rem", padding: "0.5rem" }}
            />
          </label>
          <Button type="submit">Create</Button>
        </form>
      </Card>
    </div>
  );
}
