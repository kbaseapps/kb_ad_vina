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
  console.log({ template }); // eslint-disable-line no-console
  const out = await nunjucks.renderString(template, context);
  return out;
};

let count = 0;
let output = "";

const onLoad = async (setOut: (update: string) => void) => {
  output = await renderTemplate();
  console.log({ output }); // eslint-disable-line no-console
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
    console.log("effect", { count, loaded, out, output }); // eslint-disable-line no-console
  }, [loaded, out]);
  console.log("render App", { count, out }); // eslint-disable-line no-console
  console.log({ templateURL });
  return <section dangerouslySetInnerHTML={{ __html: purify.sanitize(out) }} />;
};

export default App;
