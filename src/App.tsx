import { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./components/home";
import ICUITest from "./components/ICUITest";

function App() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/icui-test" element={<ICUITest />} />
      </Routes>
    </Suspense>
  );
}

export default App;
