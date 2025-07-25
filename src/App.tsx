import { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./components/home";
import IntegratedHome from "../tests/integration/inthome";
import { ICUITest } from "../tests/integration/icui/ICUITest";
import { ICUITest2 } from "../tests/integration/icui/ICUITest2";
import { ICUITest3 } from "../tests/integration/icui/ICUITest3";
import { ICUITest4 } from "../tests/integration/icui/ICUITest4";
import { ICUITest45 } from "../tests/integration/icui/ICUITest4.5";
import ICUITest49 from "../tests/integration/icui/ICUITest4.9";
import ICUITest61 from "../tests/integration/icui/ICUITest6.1";
import { ICUIFileMenuTest } from "./icui/components/tests/ICUIFileMenuTest";
import { ICUILayoutMenuTest } from "./icui/components/tests/ICUILayoutMenuTest";
import ICUIEditorComparison from "../tests/integration/icui/ICUIEditorComparison";
import { ICUIReferenceLayouts } from "../tests/integration/icui/ICUIReferenceLayouts";
import { ICUIMainPage } from "../tests/integration/icui/ICUIMainPage";
import { ICUITestEnhanced } from "../tests/integration/icui/ICUITestEnhanced";
import { ICUITerminalTest } from "../tests/integration/icui/icuiTerminaltest";
import ICUIServicesTest from "../tests/integration/icui/ICUIServicesTest";
import ICUIServicesPhase2Test from "../tests/integration/icui/ICUIServicesPhase2Test";
import Integration from "../tests/integration/integration";
import SimpleTerminal from "../tests/integration/simpleterminal";
import SimpleEditor from "../tests/integration/simpleeditor";
import SimpleExplorer from "../tests/integration/simpleexplorer";
import SimpleChat from "../tests/integration/simplechat";
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
          <Route path="/inthome" element={
            <BackendContextProvider>
              <IntegratedHome />
            </BackendContextProvider>
          } />
          <Route path="/integration" element={<Integration />} />
          <Route path="/simple-terminal" element={<SimpleTerminal />} />
          <Route path="/simple-editor" element={<SimpleEditor />} />
          <Route path="/simple-explorer" element={<SimpleExplorer />} />
          <Route path="/simple-chat" element={<SimpleChat />} />
          <Route path="/icui-test" element={<ICUITest />} />
          <Route path="/icui-test2" element={<ICUITest2 />} />
          <Route path="/icui-test3" element={<ICUITest3 />} />
          <Route path="/icui-test4" element={<ICUITest4 />} />
          <Route path="/icui-test4.5" element={<ICUITest45 />} />
          <Route path="/icui-test4.9" element={<ICUITest49 />} />
          <Route path="/icui-test6.1" element={<ICUITest61 />} />
          <Route path="/icui-file-menu-test" element={<ICUIFileMenuTest />} />
          <Route path="/icui-layout-menu-test" element={<ICUILayoutMenuTest />} />
          <Route path="/icui-services-test" element={<ICUIServicesTest />} />
          <Route path="/icui-services-phase2-test" element={<ICUIServicesPhase2Test />} />
          <Route path="/icui-editor-comparison" element={<ICUIEditorComparison />} />
          <Route path="/icui-layouts" element={<ICUIReferenceLayouts />} />
          <Route path="/icui-main" element={<ICUIMainPage />} />
          <Route path="/icui-enhanced" element={<ICUITestEnhanced />} />
          <Route path="/icui-terminal-test" element={<ICUITerminalTest />} />
          
          {/* Handle double slash routes */}
          <Route path="//inthome" element={<Navigate to="/inthome" replace />} />
          <Route path="//integration" element={<Navigate to="/integration" replace />} />
          
          {/* Catch-all route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
