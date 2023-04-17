import DOMPurify from "dompurify";
import * as nunjucks from "nunjucks";
import React, { FC, useEffect, useState } from "react";
import logo from "./logo.svg";
// import templateURL from "./report.liquid";
import "./App.css";

const templateURL = "/report.html";

const purify = DOMPurify(window);
nunjucks.configure({ autoescape: true });

const renderTemplate = async () => {
  const template = await (await fetch(templateURL)).text();
  console.log({ template }); // eslint-disable-line no-console
  const out = await nunjucks.renderString(template, {
    name: "alice",
    logs: [
      ["log1", { name: "Dakota" }],
      ["log2", { name: "Ziming" }],
    ],
  });
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
  // const out = "";
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
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.tsx</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
      <section dangerouslySetInnerHTML={{ __html: purify.sanitize(out) }} />
    </div>
  );
};

export default App;
