import { Suspense, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./components/home";
import IntegratedHome from "../tests/integration/inthome";
import { ICUITest } from "../tests/integration/icui/ICUITest";
import { ICUITest2 } from "../tests/integration/icui/ICUITest2";
import ICUITest6 from "../tests/integration/icui/ICUITest6";
import ICUITest7 from "../tests/integration/icui/ICUITest7";
import ICUITest83 from "../tests/integration/icui/ICUITest8.3_ChatHistory";
import { ICUIFileMenuTest } from "./icui/components/tests/ICUIFileMenuTest";
import { ICUILayoutMenuTest } from "./icui/components/tests/ICUILayoutMenuTest";
import ICUIServicesTest from "../tests/integration/icui/ICUIServicesTest";
import ICUIServicesPhase2Test from "../tests/integration/icui/ICUIServicesPhase2Test";
import Integration from "../tests/integration/integration";
import SimpleTerminal from "../tests/integration/simpleterminal";
import SimpleEditor from "../tests/integration/simpleeditor";
import SimpleExplorer from "../tests/integration/simpleexplorer";
import SimpleChat from "../tests/integration/simplechat";
import { BackendContextProvider } from "./contexts/BackendContext";
import { ChatSessionStoreProvider } from "./icui/state/chatSessionStore";
import GlobalUploadManager from './icui/components/media/GlobalUploadManager';
import { configService } from "./services/config-service";

function App() {
  // Initialize dynamic configuration on app startup
  useEffect(() => {
    configService.getConfig().then(config => {
      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Dynamic configuration initialized:', config);
      }
    }).catch(err => {
      console.warn('⚠️  Failed to load dynamic configuration:', err);
    });
  }, []);

  return (
    <div>
      <GlobalUploadManager />
      <Suspense fallback={<p>Loading...</p>}>
        <Routes>
          <Route path="/" element={
            <BackendContextProvider>
              <ChatSessionStoreProvider>
                <Home />
              </ChatSessionStoreProvider>
            </BackendContextProvider>
          } />
          <Route path="/inthome" element={
            <BackendContextProvider>
              <ChatSessionStoreProvider>
                <IntegratedHome />
              </ChatSessionStoreProvider>
            </BackendContextProvider>
          } />
          <Route path="/integration" element={<Integration />} />
          <Route path="/simple-terminal" element={<SimpleTerminal />} />
          <Route path="/simple-editor" element={<SimpleEditor />} />
          <Route path="/simple-explorer" element={<SimpleExplorer />} />
          <Route path="/simple-chat" element={<div className="h-screen w-screen"><SimpleChat /></div>} />
          <Route path="/icui-test" element={<ICUITest />} />
          <Route path="/icui-test2" element={<ICUITest2 />} />
          <Route path="/icui-test6" element={<ICUITest6 />} />
          <Route path="/icui-test7" element={<ICUITest7 />} />
          <Route path="/icui-test8.3" element={<ICUITest83 />} />
          <Route path="/icui-file-menu-test" element={<ICUIFileMenuTest />} />
          <Route path="/icui-layout-menu-test" element={<ICUILayoutMenuTest />} />
          <Route path="/icui-services-test" element={<ICUIServicesTest />} />
          <Route path="/icui-services-phase2-test" element={<ICUIServicesPhase2Test />} />
          
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
