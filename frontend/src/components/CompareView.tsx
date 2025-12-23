"use client";

import { useState, useEffect } from "react";
import { getAvailableDrugs, compareDrugs, ComparisonResult } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  ArrowLeftRight, 
  Pill, 
  AlertTriangle, 
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles
} from "lucide-react";

export function CompareView() {
  const [drugs, setDrugs] = useState<string[]>([]);
  const [drug1, setDrug1] = useState<string>("");
  const [drug2, setDrug2] = useState<string>("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDrugs();
  }, []);

  async function loadDrugs() {
    try {
      const availableDrugs = await getAvailableDrugs();
      setDrugs(availableDrugs);
      if (availableDrugs.length >= 2) {
        setDrug1(availableDrugs[0]);
        setDrug2(availableDrugs[1]);
      }
    } catch (e) {
      console.error("Failed to load drugs:", e);
    }
  }

  async function handleCompare() {
    if (!drug1 || !drug2 || drug1 === drug2) {
      setError("Please select two different drugs");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const comparison = await compareDrugs(drug1, drug2);
      setResult(comparison);
    } catch (e) {
      setError("Failed to compare drugs. Please try again.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function swapDrugs() {
    const temp = drug1;
    setDrug1(drug2);
    setDrug2(temp);
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-foreground mb-2 flex items-center gap-2">
            <ArrowLeftRight className="w-6 h-6 text-primary" />
            Drug Comparison
          </h2>
          <p className="text-muted-foreground">
            Compare two drugs side-by-side based on FDA-approved labeling
          </p>
        </div>
      </div>

      {/* Drug Selection */}
      <div className="p-6 border-b border-border bg-card/30">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center gap-4">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-muted-foreground mb-2">
              Drug 1
            </label>
            <select
              value={drug1}
              onChange={(e) => setDrug1(e.target.value)}
              className="w-full px-4 py-3 bg-secondary/50 border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Select a drug...</option>
              {drugs.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={swapDrugs}
            className="mt-6 rounded-full"
          >
            <ArrowLeftRight className="w-4 h-4" />
          </Button>

          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-muted-foreground mb-2">
              Drug 2
            </label>
            <select
              value={drug2}
              onChange={(e) => setDrug2(e.target.value)}
              className="w-full px-4 py-3 bg-secondary/50 border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Select a drug...</option>
              {drugs.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <Button
            onClick={handleCompare}
            disabled={loading || !drug1 || !drug2 || drug1 === drug2}
            className="mt-6 px-8"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Comparing...
              </>
            ) : (
              "Compare"
            )}
          </Button>
        </div>

        {error && (
          <div className="max-w-4xl mx-auto mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-6">
        {result ? (
          <div className="max-w-5xl mx-auto space-y-6">
            {/* Summary Card */}
            <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-primary" />
                  Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground/90 leading-relaxed">{result.summary}</p>
              </CardContent>
            </Card>

            {/* Comparison Grid */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Drug 1 Column */}
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-primary flex items-center gap-2">
                  <Pill className="w-5 h-5" />
                  {result.drug1}
                </h3>

                {/* Indications */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Indications
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.indications.drug1.slice(0, 5).map((ind, i) => (
                        <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span>{ind.length > 100 ? ind.slice(0, 100) + "..." : ind}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                {/* Dosing */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Dosing
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(result.dosing.drug1).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-muted-foreground capitalize">{key.replace(/_/g, " ")}:</span>
                          <span className="text-foreground font-medium">{value}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Side Effects */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Common Side Effects
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {result.side_effects.drug1.common?.slice(0, 8).map((effect, i) => (
                        <span key={i} className="px-2 py-1 bg-orange-500/10 text-orange-400 rounded-full text-xs">
                          {effect}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Warnings */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-500" />
                      Warnings
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.warnings.drug1.slice(0, 3).map((warning, i) => (
                        <li key={i} className="text-sm text-yellow-400/80">
                          • {warning}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>

              {/* Drug 2 Column */}
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-secondary-foreground flex items-center gap-2">
                  <Pill className="w-5 h-5" />
                  {result.drug2}
                </h3>

                {/* Indications */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Indications
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.indications.drug2.slice(0, 5).map((ind, i) => (
                        <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span>{ind.length > 100 ? ind.slice(0, 100) + "..." : ind}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                {/* Dosing */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Dosing
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(result.dosing.drug2).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-muted-foreground capitalize">{key.replace(/_/g, " ")}:</span>
                          <span className="text-foreground font-medium">{value}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Side Effects */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Common Side Effects
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {result.side_effects.drug2.common?.slice(0, 8).map((effect, i) => (
                        <span key={i} className="px-2 py-1 bg-orange-500/10 text-orange-400 rounded-full text-xs">
                          {effect}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Warnings */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-500" />
                      Warnings
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.warnings.drug2.slice(0, 3).map((warning, i) => (
                        <li key={i} className="text-sm text-yellow-400/80">
                          • {warning}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Shared Side Effects */}
            {result.side_effects.shared.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">
                    Shared Side Effects (Both Drugs)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {result.side_effects.shared.map((effect, i) => (
                      <span key={i} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm">
                        {effect}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Sources */}
            <div className="text-sm text-muted-foreground mt-6 pt-4 border-t border-border">
              <strong>Sources:</strong>{" "}
              {Object.entries(result.sources).map(([drug, source], i) => (
                <span key={drug}>
                  {drug}: {source}
                  {i < Object.entries(result.sources).length - 1 ? " | " : ""}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto text-center py-20">
            <ArrowLeftRight className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2">
              Select Two Drugs to Compare
            </h3>
            <p className="text-muted-foreground">
              Choose drugs from the dropdown menus above and click "Compare" to see a detailed side-by-side analysis.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

