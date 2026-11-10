// @category SideArms
import ghidra.app.script.GhidraScript;
import ghidra.program.util.DefaultLanguageService;
import ghidra.program.model.lang.*;
public class SidearmsLanguages extends GhidraScript {
 public void run() throws Exception {
  for(LanguageDescription d : DefaultLanguageService.getLanguageService().getLanguageDescriptions(false))
   if(d.getLanguageID().toString().toLowerCase().contains("z80")) println(d.getLanguageID().toString());
  try { println(DefaultLanguageService.getLanguageService().getLanguage(new LanguageID("z80:LE:16:default")).toString()); }
  catch(Exception e) { e.printStackTrace(); }
 }
}
