import { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./components/home";
import { ICUITest } from "../tests/integration/icui/ICUITest";
import { ICUITest2 } from "../tests/integration/icui/ICUITest2";
import { ICUITest3 } from "../tests/integration/icui/ICUITest3";

function App() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/icui-test" element={<ICUITest />} />
        <Route path="/icui-test2" element={<ICUITest2 />} />
        <Route path="/icui-test3" element={<ICUITest3 />} />
      </Routes>
    </Suspense>
  );
}

export default App;
