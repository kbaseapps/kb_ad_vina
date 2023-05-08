import DataTable from "datatables.net-dt";
import DOMPurify from "dompurify";
import * as nunjucks from "nunjucks";
import React, { FC, useEffect, useState } from "react";
import "./App.css";

const templateURL = "/report.html";
const templateContextURL = "/data.json";

const purify = DOMPurify(window);
nunjucks.configure({ autoescape: true });

const renderTemplate = async () => {
  const context = await (await fetch(templateContextURL)).json();
  const template = await (await fetch(templateURL)).text();
  const out = await nunjucks.renderString(template, context);
  return out;
};

let count = 0;
let output = "";

const onLoad = async (setOut: (update: string) => void) => {
  output = await renderTemplate();
  setOut(output);
};

const App: FC = () => {
  count += 1;
  const [out, setOut] = useState("Template output.");
  const [loaded, setLoaded] = useState(0);

  useEffect(() => {
    if (loaded < 1) {
      onLoad(setOut);
      setLoaded(loaded + 1);
    }
    setOut(output);
  }, [loaded, out]);
  console.log("render App", { count, out }); // eslint-disable-line no-console
  const doc = (
    <section dangerouslySetInnerHTML={{ __html: purify.sanitize(out) }} />
  );
  const table = new DataTable("#vina", { retrieve: true });
  console.log({ table }); // eslint-disable-line no-console
  return doc;
};

export default App;
