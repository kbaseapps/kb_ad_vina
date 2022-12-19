import { Liquid } from "liquidjs";
import React, { FC, useEffect, useState } from "react";
import logo from "./logo.svg";
import "./App.css";

const engine = new Liquid();

const renderTemplate = async () => {
  const out = await engine.parseAndRender("{{name | capitalize}}", {
    name: "alice",
  });
  return out;
};

let output = "";

(async () => {
  output = await renderTemplate();
})();

const App: FC = () => {
  const [out, setOut] = useState("");
  useEffect(() => {
    setOut(output);
  }, [out]);
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edxt <code>src/App.tsx</code> and save to reload.
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
      <section>Name: {out}</section>
    </div>
  );
};

export default App;
