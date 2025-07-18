import { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./components/home";
import { ICUITest } from "../tests/integration/icui/ICUITest";
import { ICUITest2 } from "../tests/integration/icui/ICUITest2";
import { ICUITest3 } from "../tests/integration/icui/ICUITest3";
import { ICUITest4 } from "../tests/integration/icui/ICUITest4";
import { ICUITest45 } from "../tests/integration/icui/ICUITest4.5";
import ICUITest49 from "../tests/integration/icui/ICUITest4.9";
import ICUIEditorComparison from "../tests/integration/icui/ICUIEditorComparison";
import { ICUIReferenceLayouts } from "../tests/integration/icui/ICUIReferenceLayouts";
import { ICUIMainPage } from "../tests/integration/icui/ICUIMainPage";
import { ICUITestEnhanced } from "../tests/integration/icui/ICUITestEnhanced";
import { ICUITerminalTest } from "../tests/integration/icui/icuiTerminaltest";
import Integration from "../tests/integration/integration";
import SimpleTerminal from "../tests/integration/simpleterminal";
import SimpleEditor from "../tests/integration/simpleeditor";
import { BackendContextProvider } from "./contexts/BackendContext";

function App() {
  return (
    <div>
      <Suspense fallback={<p>Loading...</p>}>
        <Routes>
          <Route path="/" element={
            <BackendContextProvider>
              <Home />
            </BackendContextProvider>
          } />
          <Route path="/integration" element={<Integration />} />
          <Route path="/simple-terminal" element={<SimpleTerminal />} />
          <Route path="/simple-editor" element={<SimpleEditor />} />
          <Route path="/icui-test" element={<ICUITest />} />
          <Route path="/icui-test2" element={<ICUITest2 />} />
          <Route path="/icui-test3" element={<ICUITest3 />} />
          <Route path="/icui-test4" element={<ICUITest4 />} />
          <Route path="/icui-test4.5" element={<ICUITest45 />} />
          <Route path="/icui-test4.9" element={<ICUITest49 />} />
          <Route path="/icui-editor-comparison" element={<ICUIEditorComparison />} />
          <Route path="/icui-layouts" element={<ICUIReferenceLayouts />} />
          <Route path="/icui-main" element={<ICUIMainPage />} />
          <Route path="/icui-enhanced" element={<ICUITestEnhanced />} />
          <Route path="/icui-terminal-test" element={<ICUITerminalTest />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
