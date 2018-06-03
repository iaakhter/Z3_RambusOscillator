function [I, firDerSrc, firDerGate, firDerDrain, secDerSrc, secDerGate, secDerDrain, secDerSrcGate, secDerSrcDrain, secDerGateDrain] = currentNFet(src, gate, drain, Vtp, Vtn, Vdd, Kn, Sn)
  if(nargin < 8) Sn = 8/3.0; end;
  if(nargin < 7) Kn = 1.5; end;
  if(nargin < 6) Vdd = 1.8; end;
  if(nargin < 5) Vtn = 0.3; end;
  if(nargin < 4) Vtp = -0.3; end;
  Kp = -Kn/2.0;
  Sp = Sn*2.0;

  I = 0.0;
  firDerSrc = 0.0;
  firDerGate = 0.0;
  firDerDrain = 0.0;
  secDerSrc = 0.0;
  secDerGate = 0.0;
  secDerDrain = 0.0;
  secDerSrcGate = 0.0;
  secDerSrcDrain = 0.0;
  secDerGateDrain = 0.0;
  gs = gate - src;
  ds = drain - src;

  InMax = 0.0;
  constantSrc = 0.0;
  constantGate = Vdd;
  constantDrain = Vdd;
  constantGs = constantGate - constantSrc;
  constantDs = constantDrain - constantSrc;

  if constantGs <= Vtn
    InMax = 0.0;
  elseif constantDs >= constantGs - Vtn
    InMax =  0.5*Sn*Kn*(constantGs - Vtn)*(constantGs - Vtn);
  elseif constantDs <= constantGs - Vtn
    InMax = Sn*Kn*(constantGs - Vtn - constantDs/2.0)*constantDs;
  end;
  gn = InMax/Vdd;
  
  I = 0.0;

  firDerSrc = 0.0;
  firDerGate = 0.0;
  firDerDrain = 0.0;
  secDerSrc = 0.0;
  secDerGate = 0.0;
  secDerDrain = 0.0;
  secDerSrcGate = 0.0;
  secDerSrcDrain = 0.0;
  secDerGateDrain = 0.0;
  gs = gate - src;
  ds = drain - src;

  InLeak = ds*(2 + (gs - Vtn)/Vdd)*(gn*1e-4);
  firDerLeakSrc = (gn*1e-4)*((ds)*(-1.0/Vdd) - (2 + (gs - Vtn)/Vdd));
  firDerLeakGate = (gn*1e-4)*(ds/Vdd);
  firDerLeakDrain = (gn*1e-4)*(2 + (gs - Vtn)/Vdd);
  secDerLeakSrc = (2*1e-4)*(gn/Vdd);
  secDerLeakGate = 0.0;
  secDerLeakDrain = 0.0;
  secDerLeakSrcGate = (gn*1e-4)*(-1/Vdd);
  secDerLeakSrcDrain = (gn*1e-4)*(-1/Vdd);
  secDerLeakGateDrain = (gn*1e-4)*(1/Vdd);

  if src > drain
    [I, firDerSrc, firDerGate, firDerDrain, secDerSrc, secDerGate, secDerDrain, secDerSrcGate, secDerSrcDrain, secDerGateDrain] = currentNFet(drain, gate, src, Vtp, Vtn, Vdd, Kn, Sn);
    I = -I;
    firDerSrc = -firDerSrc;
    firDerGate = -firDerGate;
    firDerDrain = -firDerDrain;
    secDerSrc = -secDerSrc;
    secDerGate = -secDerGate;
    secDerDrain = -secDerDrain;
    secDerSrcGate = -secDerSrcGate;
    secDerSrcDrain = -secDerSrcDrain;
    secDerGateDrain = -secDerGateDrain;

  else
    if (gs <= Vtn)
    	I = 0.0;
      firDerSrc = 0.0;
      firDerGate = 0.0;
      firDerDrain = 0.0;
      secDerSrc = 0.0;
      secDerGate = 0.0;
      secDerDrain = 0.0;
      secDerSrcGate = 0.0;
      secDerSrcDrain = 0.0;
      secDerGateDrain = 0.0;
    elseif (ds >= gs - Vtn)
      I = Sn*(Kn/2.0)*(gs - Vtn)*(gs - Vtn);
      firDerSrc = -Sn*Kn*(gate - src - Vtn);
      firDerGate = Sn*Kn*(gate - src - Vtn);
      firDerDrain = 0.0;
      secDerSrc = Sn*Kn;
      secDerGate = Sn*Kn;
      secDerDrain = 0.0;
      secDerSrcGate = -Sn*Kn;
      secDerSrcDrain = 0.0;
      secDerGateDrain = 0.0;
    elseif (ds <= gs - Vtn)
      I = Sn*(Kn)*(gs - Vtn - ds/2.0)*ds;
      firDerSrc = Sn*Kn*(src - gate + Vtn);
      firDerGate = Sn*Kn*(drain - src);
      firDerDrain = Sn*Kn*(gate - Vtn - drain);
      secDerSrc = Sn*Kn;
      secDerGate = 0.0;
      secDerDrain = -Sn*Kn;
      secDerSrcGate = Sn*Kn;
      secDerSrcDrain = 0.0;
      secDerGateDrain = Sn*Kn;
    end;
    if InLeak < 0
      disp('NEG INLEAK IN NFET')
      src
      gate
      drain
      InLeak
      gn
    end;
    I = I + InLeak;
    firDerSrc = firDerSrc + firDerLeakSrc;
    firDerGate = firDerGate + firDerLeakGate;
    firDerDrain = firDerDrain + firDerLeakDrain;
    secDerSrc = secDerSrc + secDerLeakSrc;
    secDerGate = secDerGate + secDerLeakGate;
    secDerDrain = secDerDrain + secDerLeakDrain;
    secDerSrcGate = secDerSrcGate + secDerLeakSrcGate;
    secDerSrcDrain = secDerSrcDrain + secDerLeakSrcDrain;
    secDerGateDrain = secDerGateDrain + secDerLeakGateDrain;

  end
end % inverter
