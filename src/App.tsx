import { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./components/home";
import { ICUITest } from "../tests/integration/icui/ICUITest";
import { ICUITest2 } from "../tests/integration/icui/ICUITest2";
import { ICUITest3 } from "../tests/integration/icui/ICUITest3";
import { ICUITest4 } from "../tests/integration/icui/ICUITest4";
import { ICUITest45 } from "../tests/integration/icui/ICUITest4.5";
import { ICUIReferenceLayouts } from "../tests/integration/icui/ICUIReferenceLayouts";
import { ICUIMainPage } from "../tests/integration/icui/ICUIMainPage";

function App() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/icui-test" element={<ICUITest />} />
        <Route path="/icui-test2" element={<ICUITest2 />} />
        <Route path="/icui-test3" element={<ICUITest3 />} />
        <Route path="/icui-test4" element={<ICUITest4 />} />
        <Route path="/icui-test4.5" element={<ICUITest45 />} />
        <Route path="/icui-layouts" element={<ICUIReferenceLayouts />} />
        <Route path="/icui-main" element={<ICUIMainPage />} />
      </Routes>
    </Suspense>
  );
}

export default App;
