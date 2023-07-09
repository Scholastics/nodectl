from concurrent.futures import ThreadPoolExecutor

from termcolor import colored, cprint
from os import system, path, environ, makedirs
from sys import exit
from getpass import getpass, getuser
from types import SimpleNamespace
from copy import deepcopy, copy
from secrets import compare_digest

from .migration import Migration
from .config import Configuration
from ..troubleshoot.logger import Logging
from ..node_service import Node
from ..troubleshoot.errors import Error_codes
from ..command_line import CLI
from ..troubleshoot.errors import Error_codes

class Configurator():
    
    def __init__(self,argv_list):
        self.log = Logging()
        self.error_messages = Error_codes()
        self.log.logger.info("configurator request initialized")

        self.debug = False
                        
        self.config_path = "/var/tessellation/nodectl/"
        self.config_file = "cn-config.yaml"

        self.detailed = False if "-a" in argv_list else "init"
        self.action = False
        self.is_all_global = False
        self.profile_details = False
        self.preserve_pass = False
        self.upgrade_needed = False
        self.restart_needed = True
        self.is_new_config = False
        self.skip_convert = False  # self.convert_config_obj()
        self.is_file_backedup = False
        self.backup_file_found = False
        self.error_msg = ""
        
        self.p12_items = [
            "nodeadmin", "key_location", "p12_name", "wallet_alias", "passphrase"
        ]
        self.profile_name_list = [] 
        
        if "help" in argv_list:
            self.prepare_configuration("edit_config")
            self.show_help()
        elif "-e" in argv_list:
            self.action = "edit"
        elif "-n" in argv_list:
            self.action = "new"

        self.prepare_configuration("new_config")
        self.setup()
        

    def prepare_configuration(self,action,implement=False):
        if action == "migrator":
            self.migrate = Migration({
            "config_obj": self.c.functions.config_obj,
            "caller": "configurator"
            })
            return
        
        self.c = Configuration({
            "action": action,
            "implement": implement,
            "argv_list": [action]
        })
        if not self.profile_details:
            self.profile_details = {}
        
        self.c.config_obj["caller"] = "config"
        self.node_service = Node({
            "config_obj": self.c.config_obj
        },False) 
        
        self.wrapper = self.c.functions.print_paragraphs("wrapper_only")
        

    def setup(self):
        option = "start"
        while True:
            top_newline = "bottom"
            self.c.functions.print_header_title({
                "line1": "NODECTL",
                "line2": "CONFIGURATION TOOL",
                "clear": True,
            })

            intro2 = "This feature of nodectl will help you initialize a new configuration or update/edit an existing configuration file."  
            intro3 = "will attempt to migrate/integrate your configurations changes in order to ensure a smooth transition and operations of your"
            
            paragraphs = [
                ["Welcome to the",0], ["nodectl",0,"blue","bold,underline"],
                ["configuration tool.",2],
            ]
            self.c.functions.print_paragraphs(paragraphs)
            
            try:
                if self.detailed == "init":
                    paragraphs = [
                        [intro2,2],
                        ["nodectl",0,"blue","bold"], [intro3,0],
                        ["Node",0,"green","underline"], ["via",0], 
                        ["nodectl",0,"blue","bold"], [".",-1],["",2],
                    
                        ["Detailed Mode:",0,"grey,on_yellow","bold,underline"],["will walk you through all steps/questions; with detailed explanations of each element of the configuration.",2],
                        ["Advanced Mode:",0,"grey,on_yellow","bold,underline"],["will be non-verbose, with no walk through explanations, only necessary questions.",2],
                        
                        ["The configuration tool does only a",0,"red","bold"], ["limited amount",0,"red","bold,underline"],
                        ["of data type or value verification. After the configuration tool creates a new configuration or edits an existing configuration, it will attempt",0,"red","bold"],
                        ["to verify the end resulting configuration.",2,"red","bold"],  

                        ["You can also choose the",0], ["-a",0,"yellow","bold"], ["option at the command line to enter advanced mode directly.",2],
                    ]

                    self.c.functions.print_paragraphs(paragraphs)
                    
                    adv_mode = False
                    if not self.debug:
                        adv_mode = self.c.functions.confirm_action({
                            "prompt": "Continue in advanced mode?",
                            "yes_no_default": "n",
                            "return_on": "y",
                            "exit_if": False
                        })
                    self.detailed = False if adv_mode == True else True
                    top_newline = "both"
            except:
                pass

            self.c.functions.print_header_title({
                "line1": "MAIN MENU",
                "show_titles": False,
                "newline": top_newline
            })
            
            if (self.action == "edit" or self.action == "help") and option != "reset":
                option = "e"
            elif self.action == "new" and option != "reset":
                option = "n"
            else:
                self.c.functions.print_paragraphs([
                    ["N",-1,"magenta","bold"], [")",-1,"magenta"], ["ew",-1,"magenta"], ["Configuration",1,"magenta"],
                    ["E",-1,"magenta","bold"], [")",-1,"magenta"], ["dit",-1,"magenta"], ["Existing Configuration",1,"magenta"],
                    ["Q",-1,"magenta","bold"], [")",-1,"magenta"], ["uit",-1,"magenta"], ["",2]
                ])
                
                option = self.c.functions.get_user_keypress({
                    "prompt": "KEY PRESS an option",
                    "prompt_color": "cyan",
                    "options": ["N","E","Q"],
                })
            
            if option.lower() == "q":
                cprint("  Configuration manipulation quit by Operator","magenta")
                self.c.functions.print_auto_restart_warning()
                exit(0)
            
            self.backup_config()
            
            if option.lower() == "n":
                self.is_new_config = self.skip_convert = True
                self.new_config()
            elif option.lower() == "e":
                self.is_new_config = self.skip_convert = False
                self.edit_config()
                
            option = "reset"
    
        
    def new_config(self):
        self.restart_needed = False
        do_build = False
        self.c.functions.print_header_title({
            "line1": "NODECTL",
            "line2": "create new configuration",
            "clear": True,
        })  
        
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["nodectl",0,"blue","bold"],
                ["offers only",0], [" two ",0,"yellow,on_blue"], ["types of new configuration builds.",2],
                
                ["nodectl can build a configuration for you based on",0], ["predefined profiles",0,"blue","bold"],
                [". These profiles are setup by the State Channel (or Layer0) companies that plan to ride on the Hypergraph.",2],
                
                ["OR",2,"yellow,on_red"],

                ["nodectl",0,"blue","bold"], ["can build a configuration based on user defined",0],
                ["step-by-step",0,"blue","bold"],["inputs.",2],

                ["Before continuing, please make sure you have the following checklist completed, to save time.",2,"yellow"],
                
                ["You should have obtained this information during the installation of your",0], ["Node",0,"blue","bold"],
                ["originally.",2],
                
                ["  - p12 file name",1,"magenta"],
                ["  - p12 file location",1,"magenta"],
                ["  - p12 passphrase",1,"magenta"],
                ["  - p12 wallet alias",1,"magenta"],
                ["  - layer0 link profile name(s)",0,"magenta"], ["|",0], ["manual only",1,"yellow"],
                ["  - custom directory locations",0,"magenta"], ["|",0], ["manual only",2,"yellow"],
                
                ["Warning!",0,"red","bold"],["Invalid entries will either be rejected at runtime or flagged as invalid by",0], 
                ["nodectl",0,"blue","bold"], ["before runtime.",0], ["nodectl",0,"blue","bold"], ["does not validate entries during the configuration entry process.",2]
            ] )

        self.c.functions.print_header_title({
            "line1": "CONFIGURATION TYPE",
            "show_titles": False,
            "newline": "bottom",
        })
        
        self.c.functions.print_paragraphs([
            ["P",-1,"magenta","bold"], [")",-1,"magenta"], ["redefined",-1,"magenta"],["Configuration",1,"magenta"], 
            ["M",-1,"magenta","bold"], [")",-1,"magenta"], ["anual",-1,"magenta"], ["Configuration",1,"magenta"],
            ["R",-1,"magenta","bold"], [")",-1,"magenta"], ["eturn Main",-1,"magenta"], ["Menu",1,"magenta"],
            ["Q",-1,"magenta","bold"], [")",-1,"magenta"], ["uit",-1,"magenta"], ["",2]
        ])  
            

        option = self.c.functions.get_user_keypress({
            "prompt": "KEY PRESS an option",
            "prompt_color": "cyan",
            "options": ["P","M","R","Q"]
        })
        
        if option == "r":
            return
        elif option == "q":
            cprint("  Configuration manipulation quit by Operator","magenta")
            exit(0)
        
        print("")
        self.build_config_obj()
                
        if option == "p":
            do_build = self.profiles()
        elif option == "m":
            do_build = self.manual_build()

        if do_build:            
            self.build_yaml(True)
            self.upgrade_needed = True
            
            self.build_service_file({
                "profiles": self.profile_name_list,
                "action": "Create",
                "rebuild": True
            })   

    # =====================================================
    # PRE-DEFINED PROFILE BUILD METHODS
    # =====================================================  
      
    def profiles(self):
        self.c.functions.print_header_title({
            "line1": "NODECTL",
            "line2": "profile based configuration",
            "clear": True,
        })  

        if self.detailed:        
            self.c.functions.print_paragraphs([
                ["Please choose the",0], ["profile",0,"blue","bold"], ["below that matches the configuration you are seeking to build.",2],
                ["If not found, please use the",0], ["manual",0,"yellow","bold"], ["setup and consult the Constellation Network Doc Hub for details.",2],
                ["You can also put in a request to have your State Channel's configuration added, by contacting a Constellation Network representative.",2],
            ])
        
        self.c.functions.print_header_title({
            "line1": "OPTIONS MENU",
            "show_titles": False,
            "newline": "bottom"
        })

        self.c.functions.print_paragraphs([
            ["1",-1,"magenta","bold"], [")",-1,"magenta"], ["Constellation MainNet",1,"magenta"], 
            ["2",-1,"magenta","bold"], [")",-1,"magenta"], ["Constellation IntegrationNet",1,"magenta"], 
            ["3",-1,"magenta","bold"], [")",-1,"magenta"], ["Constellation TestNet",1,"magenta"], 
            ["R",0,"magenta","bold"], [")",-1,"magenta"], ["R",0,"magenta","underline"], ["eturn to Main Menu",-1,"magenta"], ["",1],
            ["Q",-1,"magenta","bold"], [")",-1,"magenta"], ["Q",0,"magenta","underline"], ["uit",-1,"magenta"], ["",2],
        ])
        options = ["1","2","3","R","Q"]
        
        if self.debug:
            option = "1"
        else:
            option = self.c.functions.get_user_keypress({
                "prompt": "KEY PRESS an option",
                "prompt_color": "cyan",
                "options": options,
            })
        
        if option == "r":
            return False
        elif option == "q":
            cprint("  Configuration manipulation quit by Operator","magenta")
            exit(0)
            
        print("")

        self.get_p12_details("global")
        
        progress = {
            "text_start": "building configuration skeleton",
            "status": "running",
            "delay": .5,
            "newline": False,
        }
        self.c.functions.print_cmd_status(progress)
        
        if option == "1":
            self.edge_host0 = "l0-lb-mainnet.constellationnetwork.io"
            self.edge_host1 = "l1-lb-mainnet.constellationnetwork.io"
            self.environment = "mainnet"
        elif option == "2":
            # self.edge_host0 = "l0-lb-integrationnet.constellationnetwork.io"
            # self.edge_host1 = "l1-lb-integrationnet.constellationnetwork.io"
            self.edge_host0 = "3.101.147.116"
            self.edge_host1 = "3.101.147.116"
            # self.environment = "integrationnet"
            self.environment = "dev"
        elif option == "3":
            self.edge_host0 = "l0-lb-testnet.constellationnetwork.io"
            self.edge_host1 = "l1-lb-testnet.constellationnetwork.io"
            self.environment = "testnet"
             
        self.build_profile()
        self.c.functions.print_cmd_status({
            **progress,
            "status": "complete",
            "newline": True
        })
        
        if not self.is_all_global:
            for n in range(0,len(option)+1):
                print("")
                if self.detailed:
                    paragraph = [
                        ["During the configuration build, it was requested [selected] to not set all the p12 private information to all profiles.",2,"green"],
                        
                    ]
                    self.c.functions.print_paragraphs(paragraph)
                    
                if int(option) < 3: # dag
                    non_global = self.c.functions.confirm_action({
                        "prompt": f"Update dedicated p12 on profile dag-l{n}?",
                        "yes_no_default": "n",
                        "return_on": "y",
                        "exit_if": False
                    })
                    if non_global:
                        self.preserve_pass = False
                        self.get_p12_details(f"dag-l{n}")
                        
        return True


    # =====================================================
    # P12 BUILD METHODS
    # =====================================================
    
    def p12_single_profile(self,command_obj):
        ptype = command_obj.get("ptype","global")
        set_default = command_obj.get("set_default",False)
        get_existing_global = command_obj.get("get_existing_global",True)
        
        line_skip = 1
        new_config_warning = ""
        if self.is_new_config:
            new_config_warning = "Existing configuration will be overwritten!"
            line_skip = 2
        
        if ptype == "global_edit_prepare":
            ptype = "global"
        else:
            if get_existing_global and self.backup_file_found and not self.preserve_pass:
                self.c.functions.print_paragraphs([
                    ["An existing configuration file was found on the system.",0,"white","bold"],
                    ["nodectl will attempt to validate the existing configuration, you can safely ignore any errors.",2,"white","bold"],
                    
                    ["Do you want to preserve the existing",0,"white","bold"],
                    ["Global",0,"yellow,on_blue"], ["p12 details?",1,"white","bold"],

                    [new_config_warning,line_skip,"red"]
                ])
                self.preserve_pass = self.c.functions.confirm_action({
                    "prompt": "Preserve Global p12 details? ",
                    "yes_no_default": "n",
                    "return_on": "y",
                    "exit_if": False                
                })
            
            if self.preserve_pass and get_existing_global:
                self.prepare_configuration(f"edit_config")
                self.config_obj["global_p12"] = self.c.config_obj["global_p12"]
                if self.c.error_found:
                    self.log.logger.critical("Attempting to pull existing p12 information for the configuration file failed.  Valid inputs did not exist.")
                    self.log.logger.error(f"configurator was unable to retrieve p12 detail information during a configuration [{self.action}]")
                    self.print_error("Retrieving p12 details")
                self.prepare_configuration("new_config")
                cprint("  Existing p12 details preserved or collected","green")
                return
            
        try:
            self.sudo_user = environ["SUDO_USER"] 
        except:  
            self.sudo_user = getuser()
            
        nodeadmin_default = self.sudo_user
        location_default = f"/home/{self.sudo_user}/tessellation/"
        p12_default = ""
        alias_default = ""
        
        p12_required = False if set_default else True
        alias_required = False if set_default else True  
                           
        if set_default:
            nodeadmin_default = self.config_obj["global_p12"]["nodeadmin"]
            location_default = self.config_obj["global_p12"]["key_location"]
            p12_default = self.config_obj["global_p12"]["p12_name"]
            alias_default = self.config_obj["global_p12"]["wallet_alias"]   
        
        questions = {
            "nodeadmin": {
                "question": f"  {colored('Enter in the admin username for this Node','cyan')}",
                "description": "This is the Debian Operating system username used to administer your Node. It was created during Node installation. Avoid the 'root', 'admin', or 'ubuntu' user.",
                "default": nodeadmin_default,
                "required": False,
            },
            "key_location": {
                "question": f"  {colored('Enter in p12 file path','cyan')}",
                "description": "This is the location on your Debian Operating system where the p12 private key file is located.",
                "default": location_default,
                "required": False,
            },
            "p12_name": {
                "question": f"  {colored('Enter in your p12 file name: ','cyan')}",
                "description": "This is the name of your p12 private key file.  It should have a '.p12' extension.",
                "default": p12_default,
                "required": p12_required,
            },
            "wallet_alias": {
                "question": f"  {colored('Enter in p12 wallet alias name: ','cyan')}",
                "description": "This should be a single string (word) [connect multiple words with snake_case or dashes eg) 'my alias' becomes 'my_alias' or 'my-alias']. This is the alias (simple name) given to your p12 private key file; also known as, your wallet.",
                "default": alias_default,
                "required": alias_required,
            },
        }
        
        if self.migrate.keep_pass_visible:
            description = "Enter in a passphrase. The passphrase [also called 'keyphrase' or simply 'password'] will not be seen as it is entered. This configurator does NOT create new p12 private key files. "
            description += "The Node Operator should enter in their EXISTING p12 passphrase.  This configurator also does NOT change or alter the p12 file in ANY way. "
            description += "If the Node Operator wants to modify the p12 passphrase, the 'sudo nodectl passwd12' command can be used. "
            description += "To remove the passphrase from the configuration, enter in \"None\" as the passphrase, and confirm with \"None\"."
            
            pass_questions = {
                "passphrase": {
                    "question": f"  {colored('Enter in p12 passphrase: ','cyan')}",
                    "description": description,
                    "required": True,
                    "v_type": "pass",
                },
                "pass2": {
                    "question": f"  {colored('Confirm this passphrase: ','cyan')}",
                    "required": True,
                    "v_type": "pass",
                },
            }
  
        print("")
        
        self.c.functions.print_header_title({
            "line1": f"{ptype.upper()} PROFILE P12 ENTRY",
            "single_line": True,
            "newline": False if self.detailed else "bottom"
        })
        p12_answers = self.ask_confirm_questions(questions)
        p12_pass = {"passphrase": "None", "pass2": "None"}

        if self.migrate.keep_pass_visible:
            single_visible_str = f'{colored("Would you like to","cyan")} {colored("hide","yellow",attrs=["bold"])} {colored("the passphrase for this profile","cyan")}'
            if not self.c.functions.confirm_action({
                "prompt": single_visible_str,
                "yes_no_default": "n",
                "return_on": "y",
                "exit_if": False                
            }):
                while True:
                    confirm = True
                    p12_pass = self.ask_confirm_questions(pass_questions,False)
                    if not compare_digest(p12_pass["passphrase"],p12_pass["pass2"]):
                        confirm = False
                        cprint("  passphrase did not match","red",attrs=["bold"])
                    if '"' in p12_pass["pass2"]:
                        confirm = False
                        cprint("  passphrase cannot include quotes","red",attrs=["bold"])
                    if confirm:
                        break
                    
        if p12_answers["key_location"] != "global" and p12_answers["key_location"][-1] != "/":
            p12_answers["key_location"] = p12_answers["key_location"]+"/"
            
        return {
            **p12_answers,
            **p12_pass,
        }


    def get_p12_details(self,ptype):
        if ptype == "global":  # only do these details the first time around
            self.c.functions.print_header_title({
                "line1": "SECURITY DETAILS",
                "single_line": True,
                "newline": "bottom",
            }) 
            cprint("  Security and Authentication","cyan")
            
            if self.detailed:
                print("")  # user visual experience
            
            if self.detailed:
                paragraphs = [

                    ["A",0], ["Validator Node",0,"blue","bold"], ["cannot access the Constellation Network Hypergraph",0],
                    ["without a",0,"cyan"], ["p12 private key",0,"yellow","bold"], ["that is used to authenticate against network access regardless of PRO score or seedlist.",2],
                    ["This same p12 key file is used as your Node’s wallet and derives the DAG address from the p12 file.",2],
                    
                    ["The p12 key file should have been created during installation:",1,'yellow'],  
                    ["sudo nodectl install",2], 
                    
                    ["If you need to create a p12 private key file:",1,"yellow"],
                    ["sudo nodectl generate_p12",2],

                    ["nodectl",0,"blue","bold"], ["has three configuration options for access into various Metagraphs or Layer0 channels via a user defined configuration profile.",2],

                ]
                self.c.functions.print_paragraphs(paragraphs)

                wrapper = self.c.functions.print_paragraphs("wrapper_only")
                wrapper.subsequent_indent = f"{' ': <18}"
                
                print(wrapper.fill(f"{colored('1','magenta',attrs=['bold'])}{colored(': Global     - Setup a global wallet that will work with all profiles.','magenta')}"))
                print(wrapper.fill(f"{colored('2','magenta',attrs=['bold'])}{colored(': Dedicated  – Setup a unique p12 file per profile.','magenta')}"))
                
                text3 = ": Both       - Setup a global wallet that will work with any profiles that are configured to use the global settings; also, allow the Node to have Metagraphs that uses dedicated (individual) wallets, per State Channel or Layer0 network."
                print(wrapper.fill(f"{colored('3','magenta',attrs=['bold'])}{colored(text3,'magenta')}"))
            
            self.is_all_global = self.c.functions.confirm_action({
                "prompt": f"\n  Set {colored('ALL','yellow','on_blue',attrs=['bold'])} {colored('profile p12 wallets to Global?','cyan')}",
                "yes_no_default": "y",
                "return_on": "y",
                "exit_if": False
            })
            
            system("clear")
            
            self.c.functions.print_header_title({
                "line1": "Global Passphrase",
                "single_line": True,
                "newline": "top" if self.detailed else "both",
                "show_titles": False,
            })
            
            if self.detailed:
                global_text1 = "The global p12 file settings are required regardless of whether or not they are used."
                global_text2 = "The global settings are used to authenticate nodectl for each instance of the utility that is running."
                global_text3a = "You do not need to specify the passphrase. If you do not specify the passphrase, you will be asked "
                global_text3b = "for the global and individual passphrases on each execution of this utility; for commands that require such."
        
                paragraphs = [
                    ["IMPORTANT:",0,"red","bold"], [global_text1,2,"white","bold"],
                    
                    [global_text2,2,"white","bold"],
                    
                    [global_text3a+global_text3b,2,"white","bold"],
                    
                    ["REMINDER:",0,"yellow","bold"], ["default values are inside the",0], ["[]",0,"yellow","bold"],
                    ["brackets. To accept, just hit the",0], ["<enter>",0,"magenta","bold"], ["key.",2]
                ]
                print("")
                self.c.functions.print_paragraphs(paragraphs)
            
        answers = self.p12_single_profile({
            "ptype": ptype
        })
        
        progress = {
            "text_start": f"populating {ptype} p12 entries",
            "status": "running",
            "delay": .5,
            "newline": False,
        }
        self.c.functions.print_cmd_status(progress)
        
        if answers is not None:
            if "pass2" in answers:
                answers.pop("pass2")
        
            if ptype == "global":
                self.config_obj["global_p12"] = {}
                for k, v in answers.items():
                    self.config_obj["global_p12"][k] = v
            else:
                for k, v in answers.items():
                    self.config_obj["profiles"][ptype][k] = v
    
        self.c.functions.print_cmd_status({
            **progress,
            "delay": 0,
            "status": "complete",
            "newline": True,
        })
        
        if not self.migrate.keep_pass_visible:
            self.config_obj["global_p12"]["passphrase"] = "None"
            if ptype != "global":
                self.config_obj["profiles"][ptype]["passphrase"] = "None"
            
        # only ask to preserve passphrase on global
        self.preserve_pass = True  
    
    
    # =====================================================
    # MANUAL BUILD METHODS
    # =====================================================
    
    def manual_section_header(self, profile, header):
        self.c.functions.print_header_title(self.header_title)
        self.c.functions.print_header_title({
            "line1": f"{profile.upper()} PROFILE {header}",
            "show_titles": False,
            "single_line": True,
            "newline": False if self.detailed else "bottom"
        })
        
        
    def manual_build(self,default=True):
        
        if default: 
            self.header_title = {
                "line1": "New Manual Profile",
                "line2": "Builder",
                "show_titles": False,
                "clear": True,
                "newline": "both",
            }
            self.manual_build_setup()

        while True:
            self.manual_build_profile()
            self.manual_build_node_type()
            self.manual_build_layer()
            self.manual_build_environment()
            self.manual_build_description()
            self.manual_build_edge_point()
            self.manual_build_tcp()
            self.manual_build_service()
            self.manual_build_link()
            self.manual_build_dirs()
            self.manual_build_memory()
            self.manual_build_pro()
            self.manual_build_p12()
            
            self.build_profile()
            
            another = self.c.functions.confirm_action({
                "prompt": "Add another profile?",
                "yes_no_default": "n",
                "return_on": "y",
                "exit_if": False
            })
            if not another:
                break
            
            self.c.functions.print_header_title({
                "line1": "ANOTHER NEW PROFILE",
                "line2": f"Last Created: {self.profile_details['profile_name']}",
                "clear": True,
                "newline": "top"
            })
        
        self.c.functions.print_cmd_status({
            "text_start": "Configuration profile build complete",
            "status": "complete",
            "newline": True,
        })
        self.c.functions.print_cmd_status({
            "text_start": "Submitting for verification and build",
            "status": "running",
        })
            

    def manual_build_append(self,append_obj):
        self.profile_details = {
            **self.profile_details,
            **append_obj
        }  
        
              
    def manual_build_setup(self):
        self.c.functions.print_header_title({
            "line1": "MANUAL CONFIGURATION SETUP",
            "show_titles": False,
            "clear": True,
            "newline": "both"
        })
        
        if self.detailed:
            paragraph = [
                ["WARNING",0,"red,on_white","bold"],
                ["Please make sure you understand and know all the proper configuration settings when using this option.",2,"white"],
                
                ["Since the",0,],["advanced",0,"white","underline"],
                ["option was chosen, a brief explanation will be presented for each option.",2],
                
                ["Recommended/Default options will be presented in",0,],["[]",0,"yellow","bold"],
                ["simply hit the",0], ["<enter>",0, "magenta","bold"], ["key to accept.",2],
            ]
            self.c.functions.print_paragraphs(paragraph)
        
        self.get_p12_details("global") # adds to config_obj by default
            
        self.c.functions.print_header_title({
            "line1": "PREPARE PROFILES",
            "single_line": True,
            "newline": "both" if not self.detailed else "top"
        })
        
        
    def manual_build_profile(self,profile=False):
        default = None if not profile else profile
        required = True if not profile else False
        profile_title = profile if profile else ""
        self.manual_section_header(profile_title,"NAME")
            
        questions = {
            "profile_name": {
                "question": f"  {colored('Enter new profile name to add to this Node: ','cyan')}",
                "description": "It is important to pick a profile name that you do not want to change too often. This is because the profile name is used to create the directory structure that holds a lot of variable (changing or scaling in and out) data, changing this name in the future will cause a lot of data migration on your Node.",
                "default": default,
                "required": required,
            }
        }
        
        while True:
            self.profile_details = self.ask_confirm_questions(questions)
            
            self.c.functions.print_header_title(self.header_title)
            self.manual_section_header(self.profile_details['profile_name'],"SPECIFICS")
            
            if not self.is_duplicate_profile(self.profile_details['profile_name']):
                break
            
            self.c.functions.print_paragraphs([
                [" ERROR ",0,"yellow,on_red","bold"], ["A profile matching [",0],
                [self.profile_details['profile_name'],-1,"yellow","bold"], ["] already exists. Please try again.",-1],
                ["",2],
            ])

        print("")
        self.profile = f"[{self.profile_details['profile_name']}]"
        self.profile_name_list.append(self.profile_details['profile_name'])
        
        
    def manual_build_node_type(self,profile=False):
        # default = "validator" if not profile else self.profile_details["node_type"]
        profile = self.profile if not profile else profile

        self.manual_section_header(profile,"NODE TYPE")
        
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["",1], ["There are only two options: 'validator' and 'genesis'. Unless you are an advanced State Channel or Global Layer0 administrator, the 'validator' option should be chosen.",2,"white","bold"],
            ])
            
        self.c.functions.print_paragraphs([
            ["Constellation Node Types",1,"yellow,on_blue"],
            ["=","half","blue","bold"],
            ["V",-1,"magenta","bold"], [")",-1,"magenta"], ["alidator",-1,"magenta"], ["",1,],
            ["G",-1,"magenta","bold"], [")",-1,"magenta"], ["enesis",-1,"magenta"], ["",1,],
            ["Q",-1,"magenta","bold"], [")",-1,"magenta"], ["uit",-1,"magenta"], ["",2]            
        ])
        
        option = self.c.functions.get_user_keypress({
            "prompt": "KEY PRESS an option",
            "prompt_color": "cyan",
            "options": ["V","G","Q"],
        })
        
        if option.lower() == "q":
            return False
        if option.lower() == "v":
            node_vars = {"node_type": "validator"}
        if option.lower() == "g":
            node_vars = {"node_type": "genesis"}
            
        # questions = {
        #     "node_type": {
        #         "question": f"  {colored('The type of Node this VPS will become','cyan')}",
        #         "description": "There are only two options: 'validator' and 'genesis'. Unless you are an advanced State Channel or Global Layer0 administrator, the 'validator' option should be chosen.",
        #         "default": default,
        #         "required": False,
        #     },
        # }

        # while True:
        #     node_vars = self.ask_confirm_questions(questions)
        #     if node_vars["node_type"] == "validator" or node_vars["node_type"] == "genesis":
        #         break
        #     self.c.functions.print_paragraphs([
        #         ["invalid node type, try again [",0,"red"],
        #         ["validator",-1,"yellow","bold"], ["] or [",-1,"red"],
        #         ["genesis",-1,"yellow","bold"], ["] only.",-1,"red"], ["",1],
        #     ])
            
        self.profile_details.update(node_vars)
        return True
        
        
    def manual_build_layer(self,profile=False):
        default = "1" if not profile else self.c.config_obj["profiles"][profile]["layer"]
        profile = self.profile if not profile else profile
        
        self.manual_section_header(profile,"DLT LAYER")
        
        questions = {
            "layer": {
                "question": f"  {colored(f'What blockchain (DLT) layer is this profile {profile} running','cyan')}",
                "description": "The distributed layer technology 'DLT' generally called the blockchain ($DAG Constellation Network uses directed acyclic graph 'DAG') is designed by layer type. This needs to be a valid integer (number) between 0 and 4, for the 5 available layers. Metagraphs are generally always layer 1.",
                "default": default,
                "required": False,
            },
        }
        self.profile_details.update(self.ask_confirm_questions(questions))
        
        
    def manual_build_environment(self,profile=False):
        default = None if not profile else self.profile_details["environment"]
        profile = self.profile if not profile else profile
        required = True if not profile else False
        
        self.manual_section_header(profile,"ENVIRONMENT")  
          
        questions = {
            "environment": {
                "question": f"  {colored('Enter network environment identifier: ','cyan')}",
                "description": "The network you are connecting to (layer0 or State Channel (layer1)) may require an environment identifier used internally; by the network, to define certain operational variables. Depending on the State Channel, this is used to define customized elements within the State Channel. You should obtain this information from the Administrators of this network.",
                "default": default,
                "required": required,
            },
        }
        self.profile_details.update(self.ask_confirm_questions(questions))
        
        
    def manual_build_description(self,profile=False):
        default = None if not profile else self.profile_details["description"]
        profile = self.profile if not profile else profile

        self.manual_section_header(profile,"DESCRIPTION") 
        
        questions = {
            "description": {
                "question": f"  {colored('Enter a description for this profile: ','cyan')}",
                "description": f"This is a description for the Node Operator to help identify the usage of this profile {profile}. It is local description only and does not affect the configuration.",
                "default": default,
                "required": False,
            },
        }
        self.profile_details.update(self.ask_confirm_questions(questions))
        
        # description test
        if self.profile_details["description"] == "" or self.profile_details["description"] == None or self.profile_details["description"].strip(" ") == "":
            self.profile_details["description"] = "None"          
        
        
    def manual_build_edge_point(self,profile=False):
        if profile:
            host_default = self.profile_details["host"]
            port_default = self.profile_details["host_port"]
            https_default = "y" if self.profile_details["https"] == "True" else "n"
            required = False
        else:
            host_default = None; https_default = "n"; port_default = "80"; profile = self.profile
            required = True
            
        self.manual_section_header(profile,"EDGE POINTS") 
        
        questions = {
            "host": {
                "question": f"  {colored('Enter the edge point hostname or ip address: ','cyan')}",
                "description": "Generally a layer0 or State Channel (layer1) network should have a device on the network (most likely a load balancer type device/system/server) where API (application programming interface) calls can be directed.  These calls will hit the edge device and direct those API requests into the network.  This value can be a FQDN (full qualified domain name) hostname or IP address.  Do not enter a URL/URI (web address).  Please contact your layer0 or State Channel Administrator for this information.",
                "default": host_default,
                "required": required,
            },
            "host_port": {
                "question": f"  {colored('Enter the TCP port the network Edge device is listening on','cyan')}",
                "description": f"When listening on the network, a network connected server (edge point server entered for this profile {profile}) will listen for incoming connections on a specific TCP (Transport Control Protocol) port.  You should consult with the Layer0 or State Channel Administrators to obtain this port value.",
                "default": port_default,
                "required": False,
            },
            "https": {
                "question": f"  {colored('Is this a secure connection (https)','cyan')}",
                "description": "Does this connection ride across a secure HTTPS (hypertext transport protocol secure) connection?  If you entered in port 80 for the Edge Device connection port, this is should be answered as 'n'.",
                "default": https_default,
                "required": False,
                "v_type": "bool"
            },
        }
        answers = self.ask_confirm_questions(questions)
        if answers["https"] == "y" and answers["host_port"] != "443":
            self.c.functions.print_paragraphs([
                [" NOTE ",0,"white,on_red"], ["Hypertext Transfer Protocol Secure will not properly function",0,"red"],
                ["unless TCP",0,"red"], ["443",0,"yellow","bold"], ["is the default port number.",0,"red"],
                ["nodectl will automatically correct this.",2,"red"],
                ["Review configuration for auto corrected values, upon update completion.",2]
            ])
            answers["https"] = "n"
        elif answers["https"] == "n" and answers["host_port"] == "443":
            self.c.functions.print_paragraphs([
                [" NOTE ",0,"white,on_red"], ["Hypertext Transfer Protocol must be set to secure",0,"red"],
                ["when default TCP number",0,"red"], ["443",0,"yellow","bold"], ["is the port number.",0,"red"], 
                ["nodectl will automatically correct the key [",0,"red"], ["https",-1,"yellow"], ["].",-1,"red"],["",2],
                ["Review configuration for auto corrected values, upon update completion.",1]
            ])
            answers["https"] = "y"
            
        self.profile_details.update(answers)

            
    def manual_build_tcp(self,profile=False):
        port_start = "You must define a TCP (Transport Control Protocol) port that your Node will run on, to accept"
        port_ending = "This can be any port; however, it is highly recommended to keep the port between 1024 and 65535.  Constellation has been using ports in the 9000-9999 range. Do not reuse any ports you already defined, as this will cause conflicts. You may want to consult with your layer0 or State Channel administrator for recommended port values."

        tcp_range = [9000,9010,9020,9030,9040]
        
        try: 
            _ = int(self.profile_details["layer"])
        except:
            self.log.logger.error("invalid blockchain layer entered [{profile_details['layer']}] cannot continue")
            self.error_messages.error_code_messages({
                "error_code": "cfr-369",
                "line_code": "invalid_layer",
                "extra": self.profile_details["layer"]
            })
            
        if profile:
            public_default = self.profile_details["public"]  
            p2p_default = self.profile_details["p2p"]      
            cli_default = self.profile_details["cli"]   
        else:
            profile = self.profile
            for n, range in enumerate(tcp_range):
                if self.profile_details["layer"] == str(n):
                    public_default = f"{range}"
                    p2p_default = f"{range+1}"
                    cli_default = f"{range+2}" 
                    break
                else:
                    self.log.logger.error(f"invalid transport layer entered? [{self.profile_details['layer']}] cannot derive default values")
                    p2p_default = cli_default = public_default = None

        self.manual_section_header(profile,"TCP PORTS") 
                            
        questions = {
            "public": {
                "question": f"  {colored('Enter the public TCP port for this Node','cyan')}",
                "description": f"{port_start} public inbound traffic. {port_ending}",
                "required": False,
                "default": public_default,
            },
            "p2p": {
                "question": f"  {colored('Enter the P2P TCP port for this Node','cyan')}",
                "description": f"{port_start} peer to peer (p2p) traffic. {port_ending}",
                "required": False,
                "default": p2p_default,
            },
            "cli": {
                "question": f"  {colored('Enter the localhost TCP port for this Node','cyan')}",
                "description": f"{port_start} internal/local host requests to access its own API (application program interface). {port_ending}",
                "required": False,
                "default": cli_default,
            },
        }
        self.manual_build_append(self.ask_confirm_questions(questions))
        
        
    def manual_build_service(self,profile=False):
        default = None if not profile else self.profile_details["service"]
        required = True if not profile else False
        profile = self.profile if not profile else profile
        
        self.manual_section_header(profile,"SYSTEM SERVICES") 
        
        questions = {
            "service": {
                "question": f"  {colored(f'Enter Debian service name for this profile: ','cyan')}",
                "description": f"The Node that will run on this Debian based operating system will use a service. The service controls the server level 'under the hood' operations of this profile [{self.profile_details['profile_name']}]. Each profile runs its own service.  nodectl will create and control this service for the Node Operator. You have the ability to give it a specific name.",
                "default": default,
                "required": required
            },
        }
        self.manual_build_append(self.ask_confirm_questions(questions))
            
            
    def manual_build_link(self,profile=False): 
        dict_link = dict_link2 = dict_link3 = {}       
        link = False if not profile else True
        title_profile = self.profile if not profile else profile
        
        def print_header():
            self.manual_section_header(title_profile,"LINK SETUP") 
            
        link_description = "Generally, a State Channel will be required to link to a layer0 (Global L0) Hypergraph network to transmit "
        link_description += "consensus information between the local Node and the Validator Nodes on the Layer0 network. You should consult "
        link_description += "with your State Channel Administrators for further details. "
        link_description += "IMPORTANT: If you plan to use the recommended process of linking to Layer0 through another profile residing "
        link_description += "on this Node, enter \"self\" for the NodeId and enter \"self\" for the IP address.  Failure to do so will "
        link_description += "result in this profile \"thinking\" it is linking to a remote Node."
        
        if profile:
            print("")
            print_header()
            
            if int(self.profile_details["layer"]) < 1:
                self.c.functions.print_paragraphs([
                    ["",1],[" WARNING ",0,"red,on_yellow"], ["Generally enabling a link dependency on a",0,"red"],
                    ["layer 0",0,"red","bold,underline"], ["profile is not recommended.",1,"red"],
                ])
                if self.c.functions.confirm_action({
                    "prompt": "Cancel link setup?",
                    "yes_no_default": "y",
                    "return_on": "y",
                    "exit_if": False
                }):
                    return False
            
            enable_disable = "enable" if self.profile_details["layer0_enable"] == "False" else "disable"
            enable_disable = colored(enable_disable,"cyan",attrs=["underline","bold"])
            part_two = colored("the link for this profile:","cyan")
            questions = {
                "layer0_link": {
                    "question": f"  {colored(f'Do you want to {enable_disable} {part_two}','cyan')}",
                    "description": link_description,
                    "default": "n",
                    "required": False,                    
                }
            }
            enable_answer = self.ask_confirm_questions(questions,False)

            if enable_answer["layer0_link"].lower() == "y" or enable_answer["layer0_link"].lower() == "yes":
                if "disable" in enable_disable:  # color formatted value  
                    self.profile_details["layer0_link"] = "n"
                    self.profile_details["layer0_enable"] = "False"
                    return True # only change layer0_enable to False 
            else:
                if "enable" in enable_disable:
                    cprint("  Nothing to do","red")
                    return False
            
            self.profile_details["layer0_link"] = "y"  # revert because "disable"
            self.profile_details["layer0_enable"] = "True"
            key_default = self.profile_details["layer0_key"] if self.profile_details["layer0_key"] != "None" else "self"
            host_default = self.profile_details["layer0_host"] if self.profile_details["layer0_host"] != "None" else "self"
            port_default = self.profile_details["layer0_port"] if self.profile_details["layer0_port"] != "None" else "self"
            profile_default = self.profile_details["link_profile"] if self.profile_details["layer0_port"] != "None" else None
            
            
        else:
            if self.profile_details["layer"] == "0":
                self.profile_details["layer0_link"] = "n"
            else:
                print_header()
                questions = {
                    "layer0_link": {
                        "question": f"  {colored('Does this State Channel require a link to layer0','cyan')}",
                        "description": link_description,
                        "default": "y",
                        "required": False,
                    },    
                }
                dict_link = self.ask_confirm_questions(questions,False)
                link = True if dict_link["layer0_link"].lower() == "y" or dict_link["layer0_link"].lower() == "yes" else False
                print("")
            
            key_default = "self"
            host_default = port_default = "self"
            profile_default = None
            
        if link:
            questions = {
                "layer0_key": {
                    "question": f"  {colored('Enter the layer0 link public key','cyan')}",
                    "description": "You need to identify the public key of the Node that you going to attempt to link to. This is required for security purposes to avoid man-in-the-middle cybersecurity attacks.  It is highly recommended to use the public key of your own Node if you are running a layer0 network on the same Node as the Node running this State Channel.  In order to do this you can simply enter in 'self' and nodectl will take care of the rest.  If you are not using your own Node, you will need to obtain the public p12 key from the Node you are attempting to link through.",
                    "default": key_default,
                    "required": False,
                },    
            }
            dict_link2 = self.ask_confirm_questions(questions)  
            if dict_link2["layer0_key"] != "self":
                dict_link2["link_profile"] = "None"
                questions = { 
                    "layer0_host": {
                        "question": f"  {colored('Enter the layer0 link ip address or hostname','cyan')}",
                        "description": "You need to identify the ip address or hostname the Node that you going to attempt to link to. This value can be a FQDN (full qualified domain name) hostname or IP address.  Do not enter a URL/URI (web address). It is highly recommended to use the ip address of your own Node if you are running a layer0 network on the same Node as the Node running this State Channel.  In order to do this you can simply enter in 'self' and nodectl will take care of the rest.  If you are not using your own Node, you will need to obtain the ip address or hostname of the Node you are attempting to link through.",
                        "default": host_default,
                        "required": False,
                    },   
                    "layer0_port": {
                        "question": f"  {colored('Enter the public TCP port of the link host: ','cyan')}",
                        "description": "You need to identify the TCP (Transport Control Protocol) port that the Node that you going to attempt to link to uses for public communication. This value must match the exact TCP port of the Node you are linking through. You can find this value by reviewing the '/node/info' link from the IP address of the link host, or by contacting the Node Administrator for the host Node you are attempting to link through.",
                        "default": port_default,
                        "required": False,
                    },   
                }  
            else: 
                dict_link2["layer0_host"] = "self"
                dict_link2["layer0_port"] = "self"
                questions = {             
                    "link_profile": {
                        "question": f"  {colored('Enter the name of the profile that your Node will link with: ','cyan')}",
                        "description": "If you chose 'self' in any of the above questions, you should use the profile you created for your layer0 network.  If you are using an external Validator Node to link through, you can leave blank.",
                        "default": profile_default,
                        "required": False,
                    },    
                }
            dict_link3 = self.ask_confirm_questions(questions)
            dict_link = {
                **dict_link,
                **dict_link2,
                **dict_link3,
            }
        self.manual_build_append(dict_link)
        return True
 
 
    def manual_build_dirs(self,profile=False):   
        title_profile = self.profile if not profile else profile
        self.manual_section_header(title_profile,"DIRECTORY STRUCTURE")
    
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["",1], ["You can setup your Node to use the default directories for all definable directories.",2,"magenta"],
                [" IMPORTANT ",0,"white,on_blue"], ["Directories being migrated to (and from) must already exist.",2],
            ])
            
        dir_default = self.c.functions.confirm_action({
            "prompt": "Use defaults?",
            "yes_no_default": "y",
            "return_on": "y",
            "exit_if": False
        })
        
        sn_default = "default" if self.profile_details["layer"] == "0" else "disable"
        if dir_default:
            self.c.functions.print_cmd_status({
                "text_start": "Using defaults for directory structures",
                "status": "complete",
                "newline": True,
            })
            self.profile_details = {
                **self.profile_details,
                "snapshots": sn_default,
                "backups": "default",
                "uploads": "default"
            }            
            print("")
        else:
            up_default = bk_default = "default"
            if profile:
                sn_default = self.profile_details["snapshots"]
                up_default = self.profile_details["uploads"]
                bk_default = self.profile_details["backups"]
                
            snapshot_instructions = f"The snapshots directory is where a local copy of your Node's blockchain data is held. "
            snapshot_instructions += "This directory can get really large and needs to be maintained. Some administrators will want to move this "
            snapshot_instructions += "directory to a network attached (or other) location. This location must be a mounted directory. For inexperienced or"
            snapshot_instructions += "non-technical Node Operators, it is advised to enter in the key word 'default' here. Also note that for some Layer "
            snapshot_instructions += "1 Metagraphs (including Constellation's DAG State Channel) the snapshots directory should be set to 'disable' "
            snapshot_instructions += "as it is not used. Consult with the State Channel user guides or with their administrators for proper directory "
            snapshot_instructions += "locations. The snapshot directory should be set from the onset of the Node setup, it is dangerous to change its location "
            snapshot_instructions += "'after-the-fact'.  THIS DIRECTORY SHOULD BE A FULL PATH "
            snapshot_instructions += "( starting with a / and ending with a / ) eg) /var/snapshots/ "
            snapshot_instructions += "Warning: If you use a remotely mounted directory, this directory MUST be accessible; otherwise, nodectl will "
            snapshot_instructions += "exit with an inaccessible error."
            
            questions = {
                "snapshots": {
                    "question": f"  {colored('Enter a valid','cyan')} {colored('snapshots','yellow')} {colored('directory','cyan')}",
                    "description": snapshot_instructions,
                    "required": False,
                    "default": sn_default,
                },
                "uploads": {
                    "question": f"  {colored('Enter a valid','cyan')} {colored('uploads','yellow')} {colored('directory','cyan')}",
                    "description": f"The uploads directory is where any files that may be needed for troubleshooting or analysis are placed by nodectl. This directory should be a full path!",
                    "required": False,
                    "default": up_default
                },
                "backups": {
                    "question": f"  {colored('Enter a valid','cyan')} {colored('backups','yellow')} {colored('directory','cyan')}",
                    "description": f"The backups directory is where any files that may need to be restored or referenced at a later date are placed by nodectl. This directory should be a full path!",
                    "required": False,
                    "default": bk_default,
                },
            }
            
            answers = self.ask_confirm_questions(questions)
            
            for directory, c_path in answers.items():
                if c_path != "disable" and c_path != "default" and c_path[-1] != "/":
                    answers[directory] = c_path+"/"
            
            self.manual_build_append(answers)
 
 
    def manual_build_pro(self,profile=False):  
        title_profile = self.profile if not profile else profile
        self.manual_section_header(title_profile,"PRO SCORE - SEED-LIST")
        
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["",1], ["You can setup your Node to use the",0], ["default",0,"magenta"], ["PRO score",0,"yellow"],
                ["and",0], ["seed list",0,"yellow"], ["elements.",2,"magenta"],
            ])
            
        dir_default = self.c.functions.confirm_action({
            "prompt": "Use defaults?",
            "yes_no_default": "y",
            "return_on": "y",
            "exit_if": False
        })
        
        if dir_default:
            self.c.functions.print_cmd_status({
                "text_start": "Using defaults for PRO and SEED-LIST structures",
                "status": "complete",
                "newline": True,
            })
            if int(self.profile_details["layer"]) < 1:
                self.profile_details = {
                    **self.profile_details,
                    "seed_location": "/var/tessellation/",
                    "seed_file": "seed-list"
                }      
            else:
                self.profile_details = {
                    **self.profile_details,
                    "seed_location": "disable",
                    "seed_file": "disable"
                }                         
            print("")
        else:
            if profile:
                location_default = self.profile_details["seed_location"]
                seed_file = self.profile_details["seed_file"]
            else:
                location_default = "/var/tessellation/"
                seed_file = "seed-list"
            
            questions = {
                "seed_location": {
                    "question": f"  {colored('Enter a valid','cyan')} {colored('pro/seed','yellow')} {colored('directory','cyan')}",
                    "description": f"The PRO directory is where a local copy of your Node's Hypergraph temporary implemented access-list is held.",
                    "required": False,
                    "default": location_default,
                },
                "seed_file": {
                    "question": f"  {colored('Enter a valid','cyan')} {colored('seed-list','yellow')} {colored('file name','cyan')}",
                    "description": f"The file name is the name used to read the access-list entries.  This file must match up exactly with the current seed-list held on the Hypergraph by the other members of the network.  If the file does not match exactly, the Node attempt to authenticate to the Hypergraph will be denied.",
                    "required": False,
                    "default": seed_file
                },
            }
            
            seed_results = self.ask_confirm_questions(questions)
            
            # make sure location is proper directly semantics 
            if seed_results["seed_location"][-1] != "/":
                seed_results["seed_location"] = seed_results["seed_location"]+"/"
                
            self.manual_build_append(seed_results)
                
                
    def manual_build_memory(self,profile=False):
        xms_default = "1024M"
        xmx_default = None
        xss_default = "256K"
        required = True
        if profile:
            xms_default = self.profile_details["java_jvm_xms"]
            xmx_default = self.profile_details["java_jvm_xmx"]
            xss_default = self.profile_details["java_jvm_xss"]
            required = False
        else:
            profile = self.profile
        
        self.manual_section_header(profile,"JAVA MEMORY HEAPS")
        
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["",1], ["You can setup your Node to use the default java memory heap values.",1],
                ["K",0,"yellow","underline"], ["for kilobytes,",0], ["M",0,"yellow","underline"], ["for Megabytes, and",0], ["G",0,"yellow","underline"], ["for Gigabytes.",1],
                ["example:",0,"magenta"], ["1024M",2,"yellow"]
            ])

        questions = {
            "java_jvm_xms": {
                "question": f"  {colored('Enter the java','cyan')} {colored('Xms','yellow')} {colored('desired value','cyan')}",
                "description": "Xms is used for setting the initial and minimum heap size. The heap is an area of memory used to store objects instantiated by Node's java software running on the JVM.",
                "required": False,
                "default": xms_default,
            },
            "java_jvm_xmx": {
                "question": f"  {colored('Enter the java','cyan')} {colored('Xmx','yellow')} {colored('desired value: ','cyan')}",
                "description": "Xmx is used for setting the maximum heap size. Warning: the performance of the Node will decrease if the max heap value is set lower than the amount of live data. This can force your Node to perform garbage collections more frequently, because memory space may be needed more habitually.",
                "required": required,
                "default": xmx_default,
            },
            "java_jvm_xss": {
                "question": f"  {colored('Enter the java','cyan')} {colored('Xss','yellow')} {colored('desired value','cyan')}",
                "description": "Your Node will run multiple threads and these threads have their own stacks.  This parameter is used to limit how much memory a stack consumes.",
                "required": False,
                "default": xss_default
            },
        }
        self.manual_build_append(self.ask_confirm_questions(questions))
        
        
    def manual_build_p12(self,profile=False):
        if profile:
            self.is_all_global = False
            self.migrate.keep_pass_visible = True
            self.manual_section_header(profile,"P12 UPDATES")
            self.c.functions.print_paragraphs([
                ["",1], ["You are requesting to update the [",-1,"magenta"],["p12",-1,"yellow","bold"], 
                ["] settings for the configuration profile [",-1,"magenta"],
                [profile,-1,"yellow","bold"],["]. ",-1,"magenta"],["",2],
            ])

        self.profile_details["p12_passphrase_global"] = 'False'          
        if self.is_all_global:
            self.profile_details["p12_passphrase_global"] = 'True'
        else:
            dedicated_p12 = self.c.functions.confirm_action({
                "prompt": f"Use the global p12 settings for {colored(self.profile_details['profile_name'],'yellow')} {colored('profile?','cyan')}",
                "yes_no_default": "n",
                "return_on": "y",
                "exit_if": False
            })
            if not dedicated_p12:
                self.manual_build_append(
                    self.p12_single_profile({
                        "ptype": self.profile_details["profile_name"],
                        "get_existing_global": False,
                        "set_default": True
                    })
                )
            elif profile:
                for p12_item in self.p12_items:
                    self.profile_details[f"p12_{p12_item}_global"] = 'True'
                    self.profile_details[p12_item] = "global"
                
            return              


    # =====================================================
    # COMMON BUILD METHODS  
    # =====================================================
          
    def ask_confirm_questions(self, questions, confirm=True):
        alternative_confirm_keys = questions.get("alt_confirm_dict",{})
        if len(alternative_confirm_keys) > 0:
            alternative_confirm_keys = questions.pop("alt_confirm_dict")
            
        while True:
            value_dict = {}
            
            for key, values in questions.items():
                default = questions[key].get("default",None)
                required = questions[key].get("required",True)
                description = questions[key].get("description",None)
                v_type = questions[key].get("v_type","str")
            
                question = values["question"]
                if default != None and default != "None":
                    question = f"{question} {colored('[','cyan')}{colored(default,'yellow',attrs=['bold'])}{colored(']: ','cyan')}"

                while True:
                    if description != None and self.detailed:
                        print("")
                        self.c.functions.print_paragraphs([[description,2,"white","bold"]])
                    if v_type == "pass":
                        input_value = getpass(question)
                    else:
                        input_value = input(question)
                        if v_type == "bool":
                            if input_value.lower() == "y" or input_value.lower() == "yes":
                                input_value = "y" 
                            elif input_value.lower() == "n" or input_value.lower() == "no":
                                input_value = "n"
                            else:
                                input_value = ""
                                             
                    if required and input_value.strip() == "":
                        print(colored("  valid entry required","red"))
                    elif input_value.strip() == "":
                        input_value = "None Entered" 
                        if default != None:
                            input_value = default
                        break
                    else:
                        break

                value_dict[key] = str(input_value)

            user_confirm = True
            if confirm:
                confirm_dict = copy(value_dict)
                if len(alternative_confirm_keys) > 0:
                    for new_key, org_key in alternative_confirm_keys.items():
                        confirm_dict[new_key] = confirm_dict.pop(org_key)
                    
                self.c.functions.print_header_title({
                    "line1": "CONFIRM VALUES",
                    "show_titles": False,
                    "newline": "top"
                })
                
                paragraphs = [
                    ["If you reached this confirmation",0,"yellow"], ["unexpectedly",0, "yellow","bold,underline"], [",from the input [above] you may have hit",0,"yellow"], ["<enter>",0], 
                    ["along with your option; therefore, choosing the default.  You can choose",0,"yellow"],
                    ["n",0,"bold"], ["here and reenter the correct value.",2,"yellow"]
                ]            
                
                for key, value in confirm_dict.items():
                    paragraphs.append([f"{key.replace('_',' ')}:",0,"magenta"])
                    paragraphs.append([value,1,"yellow","bold"])                        
                self.c.functions.print_paragraphs(paragraphs)
                
                user_confirm = self.c.functions.confirm_action({
                    "prompt": f"\n  Please confirm values are as requested:",
                    "yes_no_default": "y",
                    "return_on": "y",
                    "exit_if": False
                })
                print("")
                
            if user_confirm:
                return value_dict
        
        
    def build_config_obj(self):
        self.config_obj = {
            "profiles": {},
            "auto_restart": {
                "enable": "False",
                "auto_upgrade": "False"
            },
            "global_p12": {
                "nodeadmin": "",
                "key_location": "",
                "p12_name": "",
                "wallet_alias": "",
                "passphrase": "",               
            }
        }
        
        self.config_obj["caller"] = "config" # to initialize the migration
        self.prepare_configuration("migrator")
        
        self.c.functions.print_header_title({
            "line1": "Passphrase Options",
            "show_titles": False,
            "single_line": True,
            "clear": True,
            "new_line": "both",
        })
        self.migrate.keep_pass_visible = self.migrate.handle_passphrase(False)
        
    
    def build_profile(self):
        profiles = []
        try:
            profiles.append(self.profile_details["profile_name"])
        except:
            # pre-defined selected
            self.profile_name_list = profiles = ["dag-l0","dag-l1"]
            if "integrationnet" in self.edge_host0 or "dev" in self.environment:
                self.profile_name_list = profiles = ["intnet-l0","intnet-l1"]
                
            layers = ["0","1"]
            tcp_ports = [["9000","9001","9002"],["9010","9011","9012"]]
            java = [["1024M","7G","256K"],["1024M","3G","256K"]]
            p12 = ["global","global","global","global","global"]; p12 = [p12,p12]
            node_type = ["validator","validator"]
            
            services = ["node_l0","node_l1"] 
            if "integrationnet" in self.edge_host0 or "dev" in self.environment:
                services = ["intnetserv_l0","intnetserv_l1"]   
                
            dirs = [["default","default","default"],["disable","default","default"]]
            host = [self.edge_host0,self.edge_host1]
            environment = self.environment
            description = [
                "Constellation Network Global Hypergraph",
                "Constellation Network Layer1 Metagraph" 
            ]
            link_zero = [["False","None","None","None","None"],["True","self","self","self",profiles[0]]]
            https = "False"
            port = ["80","80"]
            seed_location = ["/var/tessellation/","disable"]
            seed_file = ["seed-list","disable"]
            enable = "True"
        else: # manual
            profile_obj = self.profile_details

            if "enable" not in profile_obj:
                enable = "True"
            else:
                enable = profile_obj["enable"]
                
            # ====================
            # PREPARE MEMORY
            # ====================
            java =  [
                [
                    profile_obj["java_jvm_xms"],
                    profile_obj["java_jvm_xmx"],
                    profile_obj["java_jvm_xss"],
                ]
            ]
            
            # ====================
            # PREPARE LAYER
            # ====================
            layers = [profile_obj["layer"]]  # blockchain_invalid tested at 'manual_tcp_build'
            
            # ====================
            # PREPARE TCP PORTS
            # ====================
            try:
                int(profile_obj["public"]),
                int(profile_obj["p2p"]),
                int(profile_obj["cli"]),
            except:
                self.log.logger.error(f"invalid TCP ports given cannot continue, exiting utility public [{profile_obj['public']}], p2p [{profile_obj['p2p']}], cli [{profile_obj['cli']}]")
                self.error_messages.error_code_messages({
                    "error_code": "cfr-829",
                    "line_code": "invalid_tcp_ports",
                    "extra": f"public [{profile_obj['public']}], p2p [{profile_obj['p2p']}], cli [{profile_obj['cli']}]"
                })
            public = str(profile_obj["public"])
            p2p = str(profile_obj["p2p"])
            cli = str(profile_obj["cli"])
            tcp_ports = [[public,p2p,cli]] 
            
            # ====================
            # PREPARE EDGE POINTS
            # ====================
            try:
                port = [str(profile_obj["host_port"])]
            except:
                self.log.logger.error(f"edge point host port may be invalid [{profile_obj['host_port']}] using [80] as default")
                port = ["80"]
                
            host = [profile_obj["host"]]
            
            try:
                https = "True" if profile_obj["https"].lower() == "y" or profile_obj["https"].lower() == "yes" else "False"
            except:
                self.log.logger.error(f"new configuration build; secure https option was not a valid entry [{profile_obj['https']}] defaulting to False")
                https = "False"
                                
            # ====================
            # PREPARE DIRECTORIES
            # ====================
            dirs = [
                [profile_obj['snapshots'], profile_obj['backups'], profile_obj['uploads']]
            ]
                                
            # ====================
            # PREPARE SERVICES
            # ====================
            
            services = [profile_obj["service"]]
                        
            # ====================
            # PREPARE NODE TYPE
            # ====================
            if profile_obj["node_type"] != "validator" and profile_obj["node_type"] != "genesis":
                self.log.logger.error(f"invalid Node type entered by user [{profile_obj['node_type']}] defaulting to 'validator'")
                profile_obj["node_type"] = "validator"
                
            node_type = [profile_obj["node_type"]]
            
            # ====================
            # DESCRIPTION AND ENVIRONMENT
            # ====================
            description = [profile_obj["description"]]
            environment = profile_obj["environment"]

            # ====================
            # PREPARE SEED / PRO DETAILS
            # ====================
            seed_location = [profile_obj.get("seed_location")]
            seed_file = [profile_obj.get("seed_file")]
            
            # ====================
            # PREPARE P12 DETAILS
            # ====================
            p12_name = profile_obj.get("p12_name", "global")
            alias = profile_obj.get("wallet_alias", "global")
            passphrase = profile_obj.get("passphrase", "global")
            nodeadmin = profile_obj.get("nodeadmin", "global")
            location = profile_obj.get("key_location", "global")
            p12 = [
                [nodeadmin, location, p12_name, alias, passphrase]
            ]
            
            # ====================
            # PREPARE LINK PROFILE
            # ====================
            if profile_obj["layer0_link"].lower() == "y" or profile_obj["layer0_link"].lower() == "yes":
                link_zero = [
                    [
                        "True",
                        profile_obj["layer0_key"],
                        profile_obj["layer0_host"],
                        profile_obj["layer0_port"],
                        profile_obj["link_profile"]
                    ]
                ]
            else:
                link_zero = [["False","None","None","None","None"]]

        try:
            for n, profile in enumerate(profiles):
                profile_obj = {
                    f"{profile}": {
                        "enable": enable,
                        "layer": layers[n],
                        "https": https,
                        "host": host[n],
                        "host_port": port[n],
                        "environment": environment,
                        "public": tcp_ports[n][0],
                        "p2p":  tcp_ports[n][1],
                        "cli":  tcp_ports[n][2],
                        "service": services[n],
                        "layer0_enable": link_zero[n][0],
                        "layer0_key": link_zero[n][1],
                        "layer0_host": link_zero[n][2],
                        "layer0_port": link_zero[n][3],
                        "link_profile": link_zero[n][4],
                        "snapshots": dirs[n][0],
                        "backups": dirs[n][1],
                        "uploads": dirs[n][2],
                        "java_jvm_xms": java[n][0],
                        "java_jvm_xmx": java[n][1],
                        "java_jvm_xss": java[n][2],
                        "nodeadmin": p12[n][0],
                        "key_location": p12[n][1],
                        "p12_name": p12[n][2],
                        "wallet_alias": p12[n][3],
                        "passphrase": p12[n][4],
                        "node_type": node_type[n],
                        "description": description[n],
                        "seed_location": seed_location[n],
                        "seed_file": seed_file[n],
                    }
                } 
                
                self.config_obj["profiles"] = {
                    **self.config_obj["profiles"],
                    **profile_obj,
                }
                
        except Exception as e:
            self.log.logger.error(f"Error building user defined profile details | error [{e}]")
            self.error_messages.error_code_messages({
                "error_code": "cfr-1066",
                "line_code": "profile_build_error",
                "extra": e
            })
            
        return


    def build_service_file(self,command_obj):
        # profiles=(list of str) # profiles that service file is created against
        # action=(str) # Updating, Creating for user review
        # rebuild=(bool) # do we need to rebuild the configuration before continuing
        var = SimpleNamespace(**command_obj)
        
        if var.rebuild:
            self.build_known_skelton(1)
            
        progress = {
            "text_start": f"{var.action} Service file",
            "status": "running",
            "newline": True,
        }
        for profile in var.profiles:
            self.c.functions.print_cmd_status({
                **progress,
                "brackets": profile,
            })
        
        self.node_service.create_service_bash_file({
            "create_file_type": "service_file",
        })
        
        # build bash file is completed at start,restart,upgrade because there are 
        # multiple edits that cause the need to recreate the bash file
        # and the file will be only temporarily created.
        
        for profile in var.profiles:
            self.c.functions.print_cmd_status({
                **progress,
                "status": "complete",
                "newline": True,
            })
            
        if var.rebuild:
            self.ask_review_config()
        

    def build_yaml(self,quiet=False):
        # correlates to migration class - build_yaml
        
        # self.build_known_skelton(1)
        # sorted_profile_obj =  sorted(self.config_obj["profiles"].items(), key = lambda x: x[1]["layer"])
        sorted_profile_obj =  sorted(self.config_obj["profiles"].items(), key = lambda x: (x[1]["layer"], x[0]))
        sorted_config_obj = {"profiles": {}}
        for profile in sorted_profile_obj:
            sorted_config_obj["profiles"][profile[0]] = profile[1]
        self.config_obj["profiles"] = sorted_config_obj["profiles"]
        # self.build_yaml(True)
        
        progress = {
            "text_start": "building",
            "brackets": "cn-config.yaml",
            "text_end": "file",
            "status": "in progress",
            "status_color": "yellow",
            "newline": False,
        }
        self.c.functions.print_cmd_status(progress)

        self.migrate.create_n_write_yaml()
        
        # profile sections
        for profile in self.config_obj["profiles"].keys():
            details = self.config_obj["profiles"][profile]
            link_port = "None"
            if details["layer0_enable"] == "True":
                try:
                    link_port = self.config_obj["profiles"][details["link_profile"]]["public"]
                except:
                    link_port = details["layer0_port"]
                    try:
                        int(link_port)
                    except Exception as e:
                        self.error_messages.error_code_messages({
                            "error_code": "cfr-1137",
                            "line_code": "link_to_profile",
                            "extra": profile,
                            "extra2": details["link_profile"]
                        })

            for p_detail in self.p12_items:
                if p_detail == "passphrase":
                    try:
                        if details["p12_passphrase_global"] == "True" or self.is_all_global:
                            details[p_detail] = "global"
                    except:
                        if self.action == "new" or self.is_all_global:
                            details[p_detail] = "global"

                elif self.is_all_global:
                    details[p_detail] = "global"

            if details["passphrase"] != "None" and details["passphrase"] != "global":
                details["passphrase"] = f'"{details["passphrase"]}"'
                
            rebuild_obj = {
                "nodegarageprofile": profile,
                "nodegarageenable": details["enable"],
                "nodegaragelayer": details["layer"],
                "nodegarageedgehttps": details["https"],
                "nodegarageedgehost": details['host'],
                "nodegarageedgeporthost": details["host_port"],
                "nodegarageenvironment": details["environment"],
                "nodegaragepublic": details["public"],
                "nodegaragep2p": details["p2p"],
                "nodegaragecli":details["cli"],
                "nodegarageservice": details["service"],
                "nodegaragelinkenable": details["layer0_enable"],
                "nodegarage0layerkey": details["layer0_key"],
                "nodegarage0layerhost": details["layer0_host"],
                "nodegarage0layerport": str(link_port),
                "ndoegarage0layerlink": details["link_profile"],
                "nodegaragexms": details["java_jvm_xms"],
                "nodegaragexmx": details["java_jvm_xmx"],
                "nodegaragexss": details["java_jvm_xss"],
                "nodegaragenodetype": details["node_type"],
                "nodegaragedescription": details["description"],
                "nodegaragesnaphostsdir": details["snapshots"],
                "nodegaragebackupsdir": details["backups"],
                "nodegarageuploadsdir": details["uploads"],
                "nodegaragenodeadmin": details["nodeadmin"],
                "nodegaragekeylocation": details["key_location"],
                "nodegaragep12name": details["p12_name"],
                "nodegaragewalletalias": details["wallet_alias"],
                "nodegaragepassphrase": details["passphrase"],
                "nodegarageseedlistloc": details["seed_location"],
                "nodegarageseedlistfile": details["seed_file"],
                "create_file": "config_yaml_profile",
            }
            self.migrate.configurator_builder(rebuild_obj)
        
        
        # auto_restart and upgrade section
        rebuild_obj = {
            "nodegarageeautoenable": str(self.config_obj["auto_restart"]["enable"]),
            "nodegarageautoupgrade": str(self.config_obj["auto_restart"]["auto_upgrade"]),
            "create_file": "config_yaml_autorestart",
        }
        self.migrate.configurator_builder(rebuild_obj)
        
        # p12 section
        if self.config_obj["global_p12"]["passphrase"] != "None":
            self.config_obj["global_p12"]["passphrase"] = f'"{self.config_obj["global_p12"]["passphrase"]}"'
            
        rebuild_obj = {
            "nodegaragenodeadmin": self.config_obj["global_p12"]["nodeadmin"],
            "nodegaragekeylocation": self.config_obj["global_p12"]["key_location"],
            "nodegaragep12name": self.config_obj["global_p12"]["p12_name"],
            "nodegaragewalletalias": self.config_obj["global_p12"]["wallet_alias"],
            "nodegaragepassphrase": self.config_obj["global_p12"]["passphrase"],
            "create_file": "config_yaml_p12",
        }

        self.migrate.configurator_builder(rebuild_obj)
        
        complete = self.migrate.final_yaml_write_out()
        self.move_config_backups()
        
        if complete:
            self.c.functions.print_cmd_status({
                **progress,
                "status": "complete",
                "status_color": "green",
                "newline": True,
            })
            if not quiet:
                self.ask_review_config()
                self.c.functions.print_header_title({
                    "line1": "CONFIGURATOR UPDATED",
                    "show_titles": False,
                    "newline": "both",
                    "clear": True
                })
                self.c.functions.print_cmd_status({
                    "text_start": "Validating",
                    "brackets": "new",
                    "text_end": "config",
                    "status": "please wait",
                    "status_color": "yellow",
                    "newline": True,
                })
            
            self.move_config_backups()
            self.prepare_configuration("edit_config",True) # rebuild 
            
            press_any = False
            if self.upgrade_needed:            
                self.c.functions.print_paragraphs([
                    ["WARNING:",0,"yellow,on_blue","bold"],["This Node will need to be upgraded in order for changes to take affect.",2,"yellow"],
                    ["sudo nodectl upgrade",2,"grey,on_yellow","bold"],
                ])
                press_any = True
            elif self.restart_needed:
                self.c.functions.print_paragraphs([
                    ["WARNING:",0,"yellow,on_blue","bold"],["This Node will need to be restarted in order for changes to take affect.",2,"yellow"],
                    [" sudo nodectl restart -p all ",2,"grey,on_yellow","bold"],
                ])
                press_any = True
            if press_any:
                self.c.functions.print_any_key({})
                    
        else:
            self.error_messages.error_code_messages({
                "error_code": "cfr-1177",
                "line_code": "missing_dirs"
            })
        
        
    def build_known_skelton(self,option):
        # option == numeric request or profile name
        # make copy of complex config config_obj without reference
        self.config_obj = deepcopy(self.c.config_obj)
        
        try:
            int(option)
        except:
            for key, value in self.c.config_obj["profiles"][option].items():
                self.profile_details[key] = str(value)
        else:
            singles = ["enable","layer","environment","service","node_type","description"]
            key_replacements = {
                "xms": "java_jvm_xms",
                "xmx": "java_jvm_xmx",
                "xss": "java_jvm_xss",
            }
            for profile in self.c.config_obj["profiles"].keys():
                profile_details = {}
                
                obj = self.config_obj["profiles"][profile]
                for key, value in obj.items():
                    if key in singles:
                        profile_details[key] = str(value)
                    else:
                        for i_key, i_value in obj[key].items():
                            if i_key in key_replacements:
                                i_key = key_replacements[i_key]
                            if i_key == "enable": # layer0_link
                                i_key = "layer0_enable"
                            profile_details[i_key] = str(i_value)
                
                profile_details["layer0_link"] = "y" if profile_details["layer0_enable"] == "True" else "n"
                profile_details["profile_name"] = profile
                self.config_obj["profiles"][profile] = profile_details
        
        self.prepare_configuration("migrator")
            
            
    # =====================================================
    # EDIT CONFIG METHODS  
    # =====================================================
    
    def edit_config(self):
        return_option = "init"
        while True:
            self.prepare_configuration("edit_config",True)
            
            self.c.functions.print_header_title({
                "line1": "NODECTL EDITOR READY",
                "single_line": True,
                "clear": False,
                "newline": "both",
            })  

            if self.detailed:        
                self.c.functions.print_paragraphs([
                    ["nodectl",0,"blue","bold"], ["configuration yaml",0],["was found, loaded, and validated.",2],
                    
                    ["If the configuration found on the",0,"red"], ["Node",0,"red","underline"], ["reports a known issue;",0,"red"],
                    ["It is recommended to go through each",0,"red"],["issue",0,"yellow","underline"], ["one at a time, revalidating the configuration",0,"red"],
                    ["after each edit, in order to make sure that dependent values, are cleared by each edit",2,"red"],
                    
                    ["If not found, please use the",0], ["manual",0,"yellow","bold"], ["setup and consult the Constellation Network Doc Hub for details.",2],
                ])
            
            self.c.functions.print_header_title({
                "line1": "OPTIONS MENU",
                "show_titles": False,
                "newline": "bottom"
            })

            options = ["E","A","G","R","M","Q"]
            if return_option not in options:
                self.c.functions.print_paragraphs([
                    ["E",-1,"magenta","bold"], [")",-1,"magenta"], ["E",0,"magenta","underline"], ["dit Individual Profile Sections",-1,"magenta"], ["",1],
                    ["A",-1,"magenta","bold"], [")",-1,"magenta"], ["A",0,"magenta","underline"], ["ppend New Profile to Existing",-1,"magenta"], ["",1],
                    ["G",-1,"magenta","bold"], [")",-1,"magenta"], ["G",0,"magenta","underline"], ["lobal P12 Section",-1,"magenta"], ["",1],
                    ["R",-1,"magenta","bold"], [")",-1,"magenta"], ["Auto",0,"magenta"], ["R",0,"magenta","underline"], ["estart Section",-1,"magenta"], ["",1],
                    ["M",-1,"magenta","bold"], [")",-1,"magenta"], ["M",0,"magenta","underline"], ["ain Menu",-1,"magenta"], ["",1],
                    ["Q",-1,"magenta","bold"], [")",-1,"magenta"], ["Q",0,"magenta","underline"], ["uit",-1,"magenta"], ["",2],
                ])

                return_option = "init" # reset
                option = self.c.functions.get_user_keypress({
                    "prompt": "KEY PRESS an option",
                    "prompt_color": "cyan",
                    "options": options
                })
            else:
                option = return_option.lower()
            
            if option == "e":
                self.edit_profiles()
                return_option = self.edit_profile_sections()
            elif option == "m":
                return
            elif option == "a":
                self.edit_append_profile_global(False)
            elif option == "g": 
                self.edit_append_profile_global(True)
            elif option == "r":
                self.edit_auto_restart()
                if self.detailed:
                    self.c.functions.print_paragraphs([
                        [" WARNING ",0,"white,on_blue"], ["auto_restart was modified in the configuration.",1,"magenta"],
                        ["The configurator will not",0,"magenta"], ["disable/enable",0,"red","underline"], 
                        ["any instances of auto_restart automatically.",1,"magenta"],
                        ["To enable issue :",0,"yellow"], ["sudo nodectl auto_restart enable",1],
                        ["To disable issue:",0,"yellow"], ["sudo nodectl auto_restart disable",2],
                    ])
                    self.c.functions.print_any_key({})
                
            else:
                cprint("  Configuration manipulation quit by Operator","magenta")
                exit(0)  

                
    def edit_profiles(self):
        print("")
        self.header_title = {
            "line1": "Edit Profiles",
            "show_titles": False,
            "clear": True,
            "newline": "top",
        }       
             
        self.c.functions.print_header_title({
            "line1": "Edit Profiles",
            "single_line": True,
            "newline": "bottom",
        })  
        
        self.c.functions.print_paragraphs([
            ["nodectl",0,"blue","bold"], ["found the following profiles:",2]
        ])        
        
        # did a manual edit of the profile by node operator cause issue?
        try:
            _ = self.c.profile_obj.keys()
        except:
            self.error_messages.error_code_messages({
                "error_code": "cfr-1887",
                "line_code": "config_error",
                "extra": "format",
                "extra2": "existence",
            })
            
        for n, profile in enumerate(self.c.profile_obj.keys()):
            p_option = colored(n+1,"magenta",attrs=["bold"])
            profile = colored(f") {profile}","magenta")
            print(self.wrapper.fill(f"{p_option}{profile}"))
            
        confirm_str = colored("\n  Please enter full name of profile to edit: ","cyan")
        while True:
            option = input(confirm_str)
            if option in self.c.profile_obj.keys():
                self.profile_to_edit = option
                break
            cprint("  Invalid option - exact profile name required.","red")
            
        
    def edit_profile_sections(self,topic="EDIT"):
        menu_options = []
        
        def print_config_section():
            self.c.functions.print_header_title({
                "line1": "CONFIGURATOR SECTION",
                "line2": f"{topic}",
                "show_titles": False,
                "newline": "top",
                "clear": True
            })
        print_config_section()

        profile = self.profile_to_edit
        
        for option in self.c.profile_obj[profile].keys():
            menu_options.append(option)

        section_change_name = [
            ("edge_point","API Edge Point or Load Balancer"),
            ("environment","Hypergraph Network Environment Name"),
            ("layer", "DLT Blockchain Layer Type"),
            ("ports","API TCP Connection Ports"),
            ("service", "Debian System Service"),
            ("layer0_link","Consensus Link Connection"),
            ("dirs","Directory Structure"),
            ("java","Java Memory Heap Manipulation"),
            ("pro", "Access List Setup"),
            ("node_type","Hypergraph Node Type"),
            ("description","Policy Description"),
            ("p12","Profile Specific Private p12 Key")
        ]

        self.profile_details = {}
                        
        while True:
            do_build_profile = do_build_yaml = do_print_title = True 
            do_terminate = False
            option = 0
            
            self.edit_enable_disable_profile(profile,"prepare")
            bright_profile = colored(profile,"magenta",attrs=["bold"])
            
            print(f"{colored('  2','magenta',attrs=['bold'])}{colored(f') Change name [{bright_profile}','magenta')}{colored(']','magenta')}")
            print(f"{colored('  3','magenta',attrs=['bold'])}{colored(f') Delete profile [{bright_profile}','magenta')}{colored(']','magenta')}")
            
            option_list = ["1","2","3"]

            self.c.functions.print_header_title({
                "line1": f"CHOOSE A SECTION",
                "single_line": True,
                "newline": "both"
            })
            
            for p, section in enumerate(menu_options):
                if p > 0: # skip first element
                    n = hex(p+3)[-1].upper()
                    p_option = colored(f'{n}',"magenta",attrs=["bold"]) 
                    option_list.append(f'{n}')
                    section = [item[1] for item in section_change_name if item[0] == section]
                    section = colored(f")  {section[0]}","magenta")
                    # if p < 8:
                    #     section = section.replace(") ",")  ")
                    print(self.wrapper.fill(f"{p_option}{section}")) 
                    
            p_option = colored("H","magenta",attrs=["bold"])
            section = colored(")elp","magenta")
            print("\n",self.wrapper.fill(f"{p_option}{section}")) 
                    
            p_option = colored(" R","magenta",attrs=["bold"])
            section = colored(")eview Config","magenta")
            print(self.wrapper.fill(f"{p_option}{section}")) 
                    
            p_option = colored(" P","magenta",attrs=["bold"])
            section = colored(")rofile Menu","magenta")
            print(self.wrapper.fill(f"{p_option}{section}")) 
                    
            p_option = colored(" M","magenta",attrs=["bold"])
            section = colored(")ain Menu","magenta")
            print(self.wrapper.fill(f"{p_option}{section}")) 
                    
            p_option = colored(" Q","magenta",attrs=["bold"])
            section = colored(")uit","magenta")
            print(self.wrapper.fill(f"{p_option}{section}")) 
            print("")

            options2 = ["H","R","M","P","Q"]
            option_list.extend(options2)
            
            option = self.c.functions.get_user_keypress({
                "prompt": "KEY PRESS an option",
                "prompt_color": "cyan",
                "options": option_list,
                "quit_option": "Q",
            })
        
            if option == "m":
                return
            elif option == "p":
                return "E"
            elif option == "r":
                self.c.view_yaml_config("migrate")
                print_config_section()
            elif option == "h":
                self.show_help()

            if option.upper() not in options2:
                option = str(int(option,16))
                
                self.build_known_skelton(option)

                self.profile_details = {
                    **self.config_obj["profiles"][profile],
                    **self.profile_details,
                }

                if option == "1":
                    do_build_yaml = do_build_profile = self.edit_enable_disable_profile(profile)
                    
                elif option == "2":
                    do_terminate = do_build_yaml = self.edit_profile_name(profile)
                    do_build_profile = False
                    called_option = "Profile Name Change"
                    
                elif option == "3":
                    do_build_profile = False
                    do_terminate = True
                    do_build_yaml = self.delete_profile(profile)
                    called_option = "Delete Profile"
                    
                elif option == "4":
                    self.manual_build_layer(profile)
                    self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [layer] [{self.action}]"
                    called_option = "layer modification"
                    self.verify_edit_options({
                        "keys": ["layer"],
                        "error": "layer",
                        "types": ["int"]
                    })
                    
                elif option == "5":
                    self.manual_build_edge_point(profile)
                    self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [edge_point] [{self.action}]"
                    called_option = "Edge Point Modification"
                    self.verify_edit_options({
                        "keys": ["host","host_port","https"],
                        "error": "Edge Point",
                        "types": ["host","host_port","https"]
                    })
            
                elif option == "6":
                    self.manual_build_environment(profile)
                    called_option = "Environment modification"
                    
                elif option == "7":
                    self.tcp_change_preparation(profile)
                    self.manual_build_tcp(profile)
                    self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [TCP build] [{self.action}]"
                    called_option = "TCP modification"
                    self.verify_edit_options({
                        "keys": ["public","p2p","cli"],
                        "error": "TCP API ports",
                        "types": ["high_port","high_port","high_port"]
                    })   
                                
                elif option == "8":
                    self.edit_service_name(profile)
                    do_terminate = True
                    called_option = "Service Name Change"
                    
                elif option == "9":
                    do_terminate = do_build_yaml = self.manual_build_link(profile)
                    called_option = "Layer0 link"
                    if do_build_yaml:
                        self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [layer link] [{self.action}]"
                        self.verify_edit_options({
                            "keys": ["layer0_key","layer0_host"],
                            "error": "Layer Linking",
                            "types": ["128hex","host"],
                        })
                                    
                elif option == "10":
                    self.migrate_directories(profile)
                    called_option = "Directory structure modification"
                    
                elif option == "11":
                    self.manual_build_memory(profile)
                    self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [java heap memory] [{self.action}]"
                    called_option = "Memory modification"
                    self.verify_edit_options({
                        "keys": ["java_jvm_xms","java_jvm_xmx","java_jvm_xss"],
                        "error": "Java Memory Heap",
                        "types": ["mem_size","mem_size","mem_size"],
                    })
                    
                elif option == "12":
                    self.manual_build_p12(profile)
                    called_option = "P12 modification"
                    keys = []; types = []
                    if self.profile_details["key_location"] != "global":
                        keys.append("key_location")
                        types.append("path")
                    if self.profile_details["p12_name"] != "global":
                        keys.append("p12_name")
                        types.append("p12_name")
                    
                    if len(keys) > 0:
                        self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [p12 build] [{self.action}]"
                        self.verify_edit_options({
                            "keys": keys,
                            "error": "p12 input Error",
                            "types": types,
                        })
                    
                elif option == "13":
                    self.manual_build_pro(profile)
                    called_option = "PRO modification"
                    self.error_msg = f"Configurator found a error while attempting to edit the [{profile}] [pro seed list] [{self.action}]"
                    self.verify_edit_options({
                        "keys": ["seed_location"],
                        "error": "PRO/Seed Input Error",
                        "types": ["path"]
                    })
                    
                elif option == "14":
                    do_build_yaml = do_build_profile = self.manual_build_node_type(profile)
                    called_option = "Node type modification"
                    
                elif option == "15":
                    self.manual_build_description(profile)
                    called_option = "Description modification"
                    
                if do_build_profile:
                    self.build_profile()
                if do_build_yaml:
                    self.build_yaml()
                    
                if do_terminate:
                    self.c.functions.print_paragraphs([
                        [called_option,0,"green","bold"],["process has completed successfully.",2,"magenta"],
                        ["Please restart the",0,"magenta"],["configurator",0,"yellow,on_blue","bold"],
                        ["to reload the new configuration before continuing, if any further editing is necessary.",1,"magenta"],
                        ["sudo nodectl configure",2]
                    ])
                    exit(0)
                    
                if do_print_title:
                    print_config_section()


    def edit_auto_restart(self):
        self.c.functions.print_header_title({
            "line1": "AUTO RESTART EDITOR",
            "show_titles": False,
            "newline": "top",
        })
        
        warning = False
        self.restart_needed = self.upgrade_needed = False
        
        keys = list(self.c.config_obj["profiles"].keys())
        keys.append("global_p12")
        for profile in keys:
            if profile == "global_p12":
                if self.c.config_obj[profile]["passphrase"] == "None":
                    warning = True
                    break
            elif self.c.config_obj["profiles"][profile]["p12"]["passphrase"] == "None":
                warning = True
                break
                
        if warning:
            self.c.functions.print_paragraphs([
                [" WARNING ",0,"yellow,on_red"], ["nodectl's",0, "blue","bold"], ["auto_restart will not be able to automate authentication to the",0,"red"],
                ["Hypergrpah",0, "blue","bold"], ["unless a passphrase is present in the configuration.",2,"red"],
                ["Please make necessary changes and try again",2,"yellow"]
            ])
            self.c.functions.get_user_keypress({
                "prompt": "press any key to return to main menu",
                "prompt_color": "magenta",
                "options": ["any_key"],
            })
            return
        
        auto_restart_desc = "nodectl has a special automated feature called 'auto_restart' that will monitor your Node's on-line status. "
        auto_restart_desc += "In the event your Node is removed from 'Ready' state, or it is identified that your Node is not properly connected "
        auto_restart_desc += "to the current cluster, nodectl will attempt to bring the Node back online. "
        auto_restart_desc += "Please be aware that there are several different ways in which your Node might lose connection.  One "
        auto_restart_desc += "specific situation: It is important to understand that if Tessellation is upgraded to a new version, "
        auto_restart_desc += "nodectl will not auto_upgrade, unless the auto_upgrade feature is enabled. Please issue a "
        auto_restart_desc += "'sudo nodectl auto_restart help' for details."
        
        auto_upgrade_desc = "nodectl has a special automated feature called 'auto_upgrade' that will monitor your Node's on-line status. "
        auto_upgrade_desc += "In the event your Node is removed from the network because of a version upgrade, this feature will attempt "
        auto_upgrade_desc += "to bring your Node back up online; by including an Tessellation upgrade, with the restart. "
        auto_restart_desc += "'auto_restart' must be enabled in conjunction with 'auto_upgrade'."
        auto_upgrade_desc += "Please be aware that this can be a dangerous feature, as in the (unlikely) event there are bugs presented in the new "
        auto_upgrade_desc += "releases, your Node will be upgraded regardless.  It is important to pay attention to your Node even if this feature "
        auto_upgrade_desc += "is enabled.  Please issue a 'sudo nodectl auto_upgrade help' for details."
        
        self.build_known_skelton(1)
        
        restart = "disable" if self.config_obj["auto_restart"]["enable"] else "enable"
        upgrade = "disable" if self.config_obj["auto_restart"]["auto_upgrade"] else "enable"
        
        questions = {
            "auto_restart": {
                "question": f"  {colored('Do you want to [','cyan')}{colored(restart,'yellow',attrs=['bold'])}{colored('] auto_restart?','cyan')}",
                "description": auto_restart_desc,
                "default": "y" if restart == "disable" else "n",
                "required": False,
            },
            "auto_upgrade": {
                "question": f"  {colored('Do you want to [','cyan')}{colored(upgrade,'yellow',attrs=['bold'])}{colored('] auto_upgrade?','cyan')}",
                "description": auto_upgrade_desc,
                "default": "y" if upgrade == "disable" else "n",
                "required": False,
            },
            "alt_confirm_dict": {
                f"{restart} auto_restart": "auto_restart",
                f"{upgrade} auto_upgrade": "auto_upgrade",
            }
        }
        
        while True:
            restart_error = False
            enable_answers = self.ask_confirm_questions(questions,True)
            if restart == "disable" and upgrade == "disable":
                if enable_answers["auto_restart"] == "y" and enable_answers["auto_upgrade"] == "n":
                    restart_error = True

            if restart == "disable" and upgrade == "enable":
                if enable_answers["auto_restart"] == "y" and enable_answers["auto_upgrade"] == "y":
                    restart_error = True

            if restart == "enable" and upgrade == "enable":
                if enable_answers["auto_restart"] == "n" and enable_answers["auto_upgrade"] == "y":
                    restart_error = True
                
            if not restart_error:
                if restart == "enable" and enable_answers["auto_restart"] == "y":
                    self.c.functions.print_paragraphs([
                        ["",1], ["auto_restart",0,"yellow","bold"], ["will enabled on the next execution of nodectl",1],
                    ])
                break
            self.c.functions.print_paragraphs([
                [" ERROR ",0,"yellow,on_red"], ["auto_upgrade cannot be enabled without auto_restart, please try again.",1,"red"]
            ])

        
        self.config_obj["auto_restart"]["enable"] = "False" if enable_answers["auto_restart"] == "y" else "True"
        self.config_obj["auto_restart"]["auto_upgrade"] = "False" if enable_answers["auto_upgrade"] == "y" else "True"
        if restart == "enable":
            self.config_obj["auto_restart"]["enable"] = "True" if enable_answers["auto_restart"] == "y" else "False"
        if upgrade == "enable":
            self.config_obj["auto_restart"]["auto_upgrade"] = "True" if enable_answers["auto_upgrade"] == "y" else "False"
        
        self.build_yaml()

        
    def edit_append_profile_global(self,p12_only):
        line1 = "Edit P12 Global" if p12_only else "Append new profile"
        line2 = "Private Keys" if p12_only else "to configuration"
        
        self.header_title = {
            "line1": line1,
            "line2": line2,
            "show_titles": False,
            "clear": True,
            "newline": "both",
        }
        self.build_known_skelton(1)
        self.migrate.keep_pass_visible = True
        if p12_only:
            self.profile_details["p12_passphrase_global"] = 'True'
            self.preserve_pass = True
            self.skip_convert = True
            self.p12_single_profile({"ptype": "global"})
            new_globals = self.p12_single_profile({
                "ptype": "global_edit_prepare",
                "set_default": True
            })

            for key in self.p12_items:
                self.config_obj["global_p12"][key] = new_globals[key]
        else:
            self.manual_build(False)
            self.restart_needed = False
            
        self.build_yaml(True)    

        if not p12_only:
            self.build_service_file({
                "profiles": self.profile_name_list,
                "action": "Create",
                "rebuild": True,
            })   
                 
    
    def delete_profile(self,profile):
        self.c.functions.print_header_title({
            "line1": f"DELETE A PROFILE",
            "line2": profile,
            "single_line": True,
            "clear": True,
            "newline": "both"
        })

        notice = [
            ["",1],
            [" WARNING! ",2,"grey,on_red"],
            ["This will",0,"red"], ["not",0,"red","bold"], ["only",0,"yellow","underline"], ["remove the profile from the configuration;",0,"red"],
            ["moreover, this will also remove all",0,"red"], ["data",0,"magenta","bold,underline"], ["from the",0,"red"],
            ["Node",0,"yellow","bold"], ["pertaining to profile",0,"red"], [profile,0,"yellow","bold,underline"],["",2],
            
            ["-",0,"magenta","bold"], ["configuration",1,"magenta"],
            ["-",0,"magenta","bold"], ["services",1,"magenta"],
            ["-",0,"magenta","bold"], ["associated bash files",1,"magenta"],
            ["-",0,"magenta","bold"], ["blockchain data (snapshots)",2,"magenta"],
        ]

        confirm_notice = self.confirm_with_word({
            "notice": notice,
            "action": "change",
            "word": "YES",
            "profile": profile,
            "default": "n"
        })
        if not confirm_notice:
            return False    
        
        print("")
        self.c.functions.print_cmd_status({
            "text_start": "Starting deletion process",
            "newline": True,
        })
        self.handle_service(profile,"service")  # leave and stop first
        self.cleanup_service_file(self.profile_details["service"])
        self.config_obj["profiles"].pop(profile)

        self.c.functions.print_cmd_status({
            "text_start": f"Profile",
            "brackets": profile,
            "status": "deleted",
            "status_color": "red",
            "newline": True
        })

        return True
        
        
    def edit_profile_name(self, old_profile):
        self.c.functions.print_header_title({
            "line1": "Change Profile Name",
            "line2": old_profile,
            "clear": True,
            "show_titles": False,
        })
        
        self.c.functions.print_paragraphs([
            [" WARNING! ",0,"grey,on_red","bold"], ["This is a dangerous command and should be done with precaution.  It will migrate an entire profile's settings and directory structure.",2],
            
            ["Please make sure you know what you are doing before continuing...",2],
            
            ["Please enter in the new profile name you would like to change to at the input.",1,"magenta"]
        ])
        
        new_profile_question = colored("  new profile: ","yellow")
        while True:
            new_profile = input(new_profile_question)
            if new_profile != "":
                break
            print("\033[F",end="\r")
                
        print("")
        
        if new_profile == old_profile:
            self.log.logger.error(f"Attempt to change profile names that match, taking no action | new [{new_profile}] -> old [{old_profile}]")
            self.c.functions.get_user_keypress({
                "prompt": f"error: {new_profile} equals {old_profile}, press any key to return",
                "prompt_color": "red",
                "options": ["any_key"],
            })
            cprint("  Skipping, nothing to do!","yellow")
            return False
        
        self.c.functions.print_header_title({
            "line1": f"OLD: {old_profile}",
            "line2": f"NEW: {new_profile}",
            "clear": False,
            "show_titles": False,
        })
            
        notice = [
            ["",1], [ "NOTICE ",0,"blue,on_yellow","bold,underline"], 
            ["The Node's",0,"yellow"],["service name",0,"cyan","underline"], ["has not changed.",2,"yellow"],
            ["Although this is",0],["not",0,"yellow","bold,underline"],
            ["an issue and your Node will not be affected; moreover, this is being conveyed in case the Node Administrator wants to correlate the",0],
            ["service name",0,"cyan","underline"], ["with the",0], ["profile name",0,"cyan","underline"], [".",2]
        ]
        
        confirm_notice = self.confirm_with_word({
            "notice": notice,
            "action": "change",
            "word": "YES",
            "profile": new_profile,
            "default": "n"
        })
        if not confirm_notice:
            return False

        self.profile_details["profile_name"] = new_profile
        # change the key for the profiles
        self.c.config_obj["profiles"][new_profile] = self.c.config_obj["profiles"].pop(old_profile)
        self.config_obj["profiles"][new_profile] = self.config_obj["profiles"].pop(old_profile)
        
        dir_progress = {
            "text_start": "updating directory structure",
            "status_color": "yellow",
            "newline": True,
        }
        dirs = ["snapshots","backups","uploads"]
        self.c.functions.print_cmd_status({
            "text_start": "Update data link dependencies",
            "status_color": "green",
            "status": "complete",
            "newline": True,
        })
        for replace_link_p in self.c.config_obj["profiles"].keys():
            if self.c.config_obj["profiles"][replace_link_p]["layer0_link"]["link_profile"] == old_profile:
                self.config_obj["profiles"][replace_link_p]["link_profile"] = new_profile
            for dir_p in dirs:
                if old_profile in self.config_obj["profiles"][replace_link_p][dir_p]: 
                    self.c.functions.print_cmd_status({
                        **dir_progress,
                        "status": dir_p,
                    })
                    dir_value = self.config_obj["profiles"][replace_link_p][dir_p]
                    self.config_obj["profiles"][replace_link_p][dir_p] = dir_value.replace(old_profile,new_profile)
                
        self.build_service_file({
            "profiles": [new_profile],
            "action": "Updating",
            "rebuild": False,
        })
        
        progress = {
            "text_start": f"Changing profile name {old_profile}",
            "brackets": new_profile,
            "status": "running"
        }
        self.c.functions.print_cmd_status(progress)
        self.log.logger.debug(f"configurator edit request - moving [{old_profile}] to [{new_profile}]")
        
        try:
            system(f"mv /var/tessellation/{old_profile}/ /var/tessellation/{new_profile}/ > /dev/null 2>&1")
            pass
        except:
            self.error_messages.error_code_messages({
                "error_code": "cfr-2275",
                "line_code": "not_new_install",
            })

        self.c.functions.print_cmd_status({
            **progress,
            "status": "complete",
        })  
        
        self.log.logger.info(f"Changed profile names | new [{new_profile}] -> old [{old_profile}]")
        return True                  

    
    def edit_service_name(self, profile):
        self.manual_build_service(profile)
        self.cleanup_service_file(self.config_obj["profiles"][profile]["service"])
        self.c.config_obj["profiles"][profile]["service"] = self.profile_details["service"]
        self.build_service_file({
            "profiles": [profile], 
            "action": "Create",
            "rebuild": False,
            })
        
        
    def edit_enable_disable_profile(self, profile, task="None"):
        c_enable_disable = f"enable {profile} [{colored('disabled','magenta',attrs=['bold'])}{colored(']','magenta')}"
        enable_disable = "enable"
        if self.c.profile_obj[profile]["enable"] == True:
            c_enable_disable = f"disable {profile} [{colored('enabled','magenta',attrs=['bold'])}{colored(']','magenta')}" 
            enable_disable = "disable"
        c_enable_disable = colored(f') {c_enable_disable}','magenta')

        if task == "prepare":            
            self.c.functions.print_header_title({
                "line1": profile,
                "single_line": True,
                "newline": "both",
            })
            print(f"{colored('  1','magenta',attrs=['bold'])}{c_enable_disable}")
        else:
            if enable_disable == "enable":
                new = "True"; new_v = "disable" 
                old_v = "enable"
            else:
                new = "False"; new_v = "enable"
                old_v = "disable"
            
            confirmation = self.edit_confirm_choice(new_v,old_v,"enable", profile)
            if confirmation:
                self.profile_details["enable"] = new
                return True
            return False

        
    def edit_confirm_choice(self, old, new, section, profile):
        self.c.functions.print_paragraphs([
            ["",1],["For section [",0], [section,-1,"yellow","bold"], ["]",-1],["",1],
            ["Are you sure you want to change [",-1], [old,-1,"red","bold"], ["] to [",-1], [new,-1,"green","bold"],["]?",-1],["",1]
        ])   
        
        if self.c.functions.confirm_action({
            "yes_no_default": "y",
            "return_on": "y",
            "prompt": f"Confirm choice to {new}?",
            "exit_if": False
        }):
            warning_confirm = True
            if section == "enable" and new == "disable":
                for replace_link_p in self.c.config_obj["profiles"].keys():
                    if self.c.config_obj["profiles"][replace_link_p]["layer0_link"]["link_profile"] == profile:
                        self.c.functions.print_paragraphs([
                            [" WARNING ",0,"red,on_yellow"], ["Selected Profile [",0], [replace_link_p,-1,"yellow"], 
                            ["] seems to be reliant on [",-1], [profile,-1,"yellow","bold"], ["]. Continuing will",-1],
                            ["introduce possible errors.  Either remove the dependent profile from the other profiles before",0],
                            ["continuing, quit, or proceed with this understanding.",2]
                        ])
                        warning_confirm = self.c.functions.confirm_action({
                            "yes_no_default": "n",
                            "return_on": "y",
                            "prompt": f"Still perform {new}?",
                            "prompt_color": "red",
                            "exit_if": False
                        })
            if warning_confirm:        
                return True
        cprint("  Action cancelled","red")
        return False
    
          
    def edit_globals(self):
        pass
    
    
    # =====================================================
    # OTHER
    # =====================================================
    
    def backup_config(self):
        print("")
        if not self.is_file_backedup:
            progress = {
                "text_start": "Backup",
                "brackets": "cn-config.yaml",
                "text_end": "if exists",
                "status": "checking",
                "status_color": "yellow",
            }
            self.c.functions.print_cmd_status(progress)
            if path.isfile(f"/var/tessellation/nodectl/cn-config.yaml"):
                self.backup_file_found = True
                dest = "nodectl"
                if path.isdir(f"/var/tessellation/backups/"):
                    dest = "backups"
                c_time = self.c.functions.get_date_time({"action":"datetime"})
                dest = f"/var/tessellation/{dest}/cn-config_{c_time}"
                system(f"cp /var/tessellation/nodectl/cn-config.yaml {dest} > /dev/null 2>&1")
                self.c.functions.print_cmd_status({
                    **progress,
                    "status": "complete",
                    "status_color": "green",
                    "newline": True,
                })
                self.c.functions.print_paragraphs([
                    ["A previous",0], ["cn-config.yaml",0,"yellow"],
                    ["was found on the system.",2],
                    
                    ["In the event the backup directory was not found, a backup was created in the existing directory. The location is shown below.",1],
                    [dest,2,"blue","bold"]
                ])
            else:
                self.c.functions.print_cmd_status({
                    **progress,
                    "status": "skipped",
                    "status_color": "red",
                    "newline": True,
                })
                print(colored("  existing config not found","red"))
                
            self.c.functions.print_any_key({})

        self.is_file_backedup = True       


    def show_help(self):
        cli = CLI({
            "caller": "config",
            "config_obj": self.c.config_obj,
            "ip_address": None,
            "command": "help",
            "version_obj": None
        })
        
        cli.version_obj = cli.functions.get_version({"which": "nodectl_all"})
        
        cli.functions.print_help({
                "nodectl_version_only": True,
                "title": True,
                "extended": "configure",
                "usage_only": False,
                "hint": False,
        })
       
    
    def migrate_directories(self,profile):
        dir_list = ["snapshots","uploads","backups"]
        migration_dirs = {}; values = []
        
        for dir in dir_list:
            migration_dirs[dir] = {
                "old_name": self.profile_details[dir],
                "changed": False
            }
            
        self.manual_build_dirs(profile)

        for key in self.profile_details.keys():
            if key in dir_list:
                values.append(self.profile_details[key])    
                
        verified = self.c.verify_profile_types({
            "profile": profile,
            "section": "dirs",
            "values": values,
            "types": ["path","path","path"],
            "key_list": dir_list,
            "return_on": True,
        })
        if not verified:
            self.log.logger.error(f"During edit session a directory path was determined to be invalid or non-existent, causing an error to be triggered. action [{self.action}]")
            self.print_error("directory migration")
                            
        for dir in dir_list:
            if self.profile_details[dir] != migration_dirs[dir]["old_name"]:
                migration_dirs[dir] = {
                    **migration_dirs[dir],
                    "new_name": self.profile_details[dir],
                    "changed": True
                }
                
        migration_dirs["profile"] = profile
                
        def file_dir_error(directory, new_path):
            self.c.functions.print_clear_line()
            self.c.functions.print_paragraphs([
                ["An error occurred attempting to automate the creation of [",-1,"red"],[f"{new_path}",-1,"yellow","bold"],
                ["]",-1,"red"],[f". In the event that you are attempting to point your Node's {directory} towards",0,"red"],
                ["an external storage device, nodectl will continue the configuration change without migrating",0,"red"],
                [f"the {directory} to the new user defined location.",0,"red"],["nodectl will leave this up to the Node Operator.",2],
            ])
            if directory == "snapshots":
                self.c.functions.print_paragraphs([
                    ["In the event you are attempting to change the location of your snapshot storage to an external device please keep",0],
                    ["in mind that not migrating your snapshots should",0], ["not",0,"red"], ["cause any issues; other than, you may",0],
                    ["incur extra I/O on your Node while the snapshots are re-downloaded for proper Node functionality",2],
                    
                    ["Also",0], ["warning",0,"yellow","bold"], ["attempting to share snapshot external storage between multiple Nodes",0],
                    ["for any operations other than 'reading', may cause race conditions and 'out of memory' errors.",2],
                ])
                         
        def check_for_default(directory, new_path, old_path):
            path_list = [new_path,old_path]; updated_path_list = []
            for c_path in path_list:
                if c_path == "default":
                    updated_path_list.append(f"/var/tessellation/{profile}/data/snapshot/") if directory == "snapshots" else updated_path_list.append(f"/var/tessellation/{directory}")
                else:
                    updated_path_list.append(c_path) 
                        
            return updated_path_list
                           
        profile = migration_dirs.pop("profile")   
        for directory, values in migration_dirs.items():
            status = "skipped"
            status_color = "yellow"
            
            if values["changed"]:
                new_path = values["new_name"]
                old_path = values["old_name"]
                
                new_path, old_path = check_for_default(directory, new_path, old_path)
                    

                if new_path != "disable":
                    do_migration = True
                    
                    if directory == "snapshots":
                        self.c.functions.print_paragraphs([
                            [" Required: ",0,"grey,on_yellow"],
                            ["In order to migrate the snapshots directory to a custom location, the profile's service will be",0,"red"],
                            ["stopped",0,"red","underline,bold"],[".",-1,"red"], ["",2]
                        ])
                        self.handle_service(profile,"location")
                        
                    progress = {
                        "text_start": "Migrating directory",
                        "brackets": directory,
                        "text_end": "location",
                        "status": "migrating",
                        "status_color": "magenta",
                        "delay": .8,
                    }                    
                    self.c.functions.print_cmd_status(progress)
                            
                    if not path.exists(new_path):
                        try:
                            makedirs(new_path)
                        except Exception as e:
                            self.log.logger.error(f"unable to create new [{new_path}] directory from configurator - migration issue | error [{e}]")
                            file_dir_error(directory, new_path)
                            do_migration = False

                    if do_migration:
                        if not path.exists(old_path) and old_path != "disable":
                            self.log.logger.error(f"unable to find [old] directory from configurator - unable to migrate. | old path not found [{old_path}]")
                            file_dir_error(directory, new_path)
                            do_migration = False
                        elif old_path != "disable":
                            old_path = f"{old_path}/" if old_path[-1] != "/" else old_path
                            new_path = f"{new_path}/" if new_path[-1] != "/" else new_path
                            
                        if old_path != new_path:
                            if directory == "snapshots":
                                self.c.functions.print_paragraphs([
                                    ["",1], [" NOTE: ",0,"grey,on_red","bold"],
                                    ["The snapshot directory may be very large and take some time to transfer.",0,"yellow"],
                                    ["Please exercise patience during the migration.",1,"yellow"]
                                ])
                            
                            with ThreadPoolExecutor() as executor:
                                self.c.functions.event = True
                                _ = executor.submit(self.c.functions.print_spinner,{
                                    "msg": "migrating files please wait ",
                                    "color": "magenta",
                                    "newline": "both"
                                    })
                                cmd = f"rsync -a --remove-source-files {old_path} {new_path} > /dev/null 2>&1"
                                system(cmd)
                                cmd = f"rm -rf {old_path} > /dev/null 2>&1"
                                system(cmd)
                                self.c.functions.event = False
                            if path.exists(old_path):
                                clean_up = {
                                    "text_start": "Cleaning up directories",
                                    "brackets": directory,
                                    "newline": True
                                }
                                confirm = self.c.functions.confirm_action({
                                    "yes_no_default": "n",
                                    "return_on": "y",
                                    "prmopt": "Do you want to remove the old directory?",
                                    "exit_if": False
                                })
                                if confirm:                                
                                    system(f"rm -rf {old_path} > /dev/null 2>&1")
                                    self.c.functions.print_cmd_status({
                                        **clean_up,
                                        "status": "complete",
                                        "status_color": "green",
                                    })
                                else:
                                    self.c.functions.print_cmd_status({
                                        **clean_up,
                                        "status": "skipped",
                                        "status_color": "yellow",
                                    })
                            status = "complete"
                            status_color = "green"
                                    
                self.c.functions.print_cmd_status({
                    **progress,
                    "status": status,
                    "status_color": status_color,
                    "newline": True
                })
        

    def cleanup_service_file(self,service):
        self.c.functions.print_cmd_status({
            "text_start": "Cleaning up old service files",
            "status": "running",
        })  
        
        old_service = f"/etc/systemd/system/cnng-{service}.service"
        if path.exists(old_service):
            self.log.logger.debug(f"configurator edit request - removing deprecated [service] file [{service}]")
            system(f"rm -f {old_service} > /dev/null 2>&1")
            
        old_service = f"/usr/local/bin/cnng-{service}"
        if path.exists(old_service):
            self.log.logger.debug(f"configurator edit request - removing deprecated [bash] file [{service}]")
            system(f"rm -f {old_service} > /dev/null 2>&1")
            
        self.c.functions.print_cmd_status({
            "text_start": "Cleaning up old service file",
            "status": "complete",
            "newline": True,
        })        
                

    def tcp_change_preparation(self,profile):
        if self.detailed:
            self.c.functions.print_paragraphs([
                ["",1], ["In order to complete this edit request, this",0],
                ["Node profile",0,"cyan","underline"], [profile,0,"yellow","bold"],
                ["must be stopped.",2],
            ])
        else:
            # only ask if advanced (detailed) mode is on
            stop = self.c.functions.confirm_action({
                "yes_no_default": "y",
                "return_on": "y",
                "prompt": "Do you want to stop services before continuing?",
                "exit_if": False
            })      
            if not stop:
                stop = self.c.functions.confirm_action({
                    "yes_no_default": "y",
                    "return_on": "y",
                    "prompt": "Are you sure you want to continue without stopping?",
                    "exit_if": True
                })   
        self.handle_service(profile,profile)


    def print_error(self,section):
        self.c.functions.print_paragraphs([
            ["",1], [" ERROR ",0,"grey,on_red","bold"],
            ["During the configuration editing session [",0,"red"],
            [section,-1,"yellow","bold"], ["] an incorrect input was detected",-1,"red"],["",2],
            
            [" HINT ",0,"grey,on_yellow","bold"], ["If attempting to change directory structure or any elements,",0],
            ["the directory structure must exist already.",2],
            
            ["Please review the nodectl logs and/or Node operator notes and try again",1],
            ["Press",0,"magenta"], [" any key ",0,"grey,on_cyan","bold"], ["to return to the main menu",1,"magenta"]
        ])
        
        if not self.is_new_config:
            _ = self.c.functions.get_user_keypress({
                "prompt": "",
                "prompt_color": "cyan",
                "options": ["any_key"]
            })
            self.edit_profile_sections("RETRY")
        else:
            exit(1)
        
    
    def verify_edit_options(self,command_obj):
        var = SimpleNamespace(**command_obj)
        
        values = []
        for key in var.keys:
            values.append(self.profile_details[key])

        verified = self.c.verify_profile_types({
            "profile": self.profile_to_edit,
            "section": "edit_section",
            "values": values,
            "types": var.types,
            "key_list": var.keys,
            "return_on": True,
        })
        if not verified:
            self.log.logger.error(self.error_msg)
            self.print_error(var.error)   
                  

    def confirm_with_word(self,command_obj):
        notice = command_obj.get("notice",False)
        word = command_obj.get("word")
        action = command_obj.get("action")
        profile = command_obj.get("profile")
        default = command_obj.get("default","n")  # "y" or "n"
        
        confirm_str = f"{colored(f'  Confirm {action} by entering exactly [','cyan')} {colored(f'YES-{profile}','green')} {colored(']','cyan')}: "
        confirm = input(confirm_str)
        
        def word_any_key(prompt):
            print("")
            self.c.functions.get_user_keypress({
                "prompt": prompt,
                "prompt_color": "red",
                "options": ["any_key"],
            })      
                  
        if f"{word}-{profile}" == confirm:
            if self.detailed:
                self.c.functions.print_paragraphs(notice)

            if notice:
                confirm_notice = self.c.functions.confirm_action({
                    "yes_no_default": default,
                    "return_on": "y",
                    "prompt": "Continue?",
                    "exit_if": False
                })
                if not confirm_notice:
                    word_any_key("action cancelled by Node Operator, press any key")
                    return False    
                
            return True
        
        word_any_key("confirmation phrase did not match, cancelling operation, press any key")
        return False
        
            
    def convert_config_obj(self):
        # self.c.functions.print_json_debug(self.config_obj,False)
        
        sections = deepcopy(self.c.test_dict)
        sections.pop("top"); sections.pop("profiles")
        sections["java"] = ["java_jvm_xms","java_jvm_xms","java_jvm_xms"]
        sections["layer0_link"][0] = "layer0_enable"
        singles = ["enable","layer","environment","service","node_type","description"]
        
        for profile in self.c.config_obj["profiles"].keys():
            for section in self.c.config_obj["profiles"][profile].keys():
                if section in singles:
                  self.c.config_obj["profiles"][profile][section] = self.profile_details[section]

            for subsection in sections:
                for item in sections[subsection]:
                    self.c.config_obj["profiles"][profile][subsection][item] = self.profile_details[item]
        

    def handle_service(self,profile,s_type):
        # user will be notified to do a full restart at the of the process
        # to return to the network instead of doing it here.  This will ensure
        # all updates are enabled/activated/updated.
        
        self.c.functions.config_obj = self.node_service.config_obj
        self.c.functions.get_service_status()
        service = self.profile_details["service"]
        self.node_service.profile = profile
        
        actions = ["leave","stop"]
        for s_action in actions:
            if self.node_service.config_obj["node_service_status"][profile] == "inactive (dead)":
                break
            self.c.functions.print_cmd_status({            
                "text_start": "Updating Service",
                "brackets": f"{service} => {s_action}",
                "text_end": s_type,
                "status": "stopping",
                "status_color": "yellow",
                "delay": .8
            })
            self.node_service.change_service_state({
                "profile": profile,
                "action": s_action,
                "cli_flag": True,
                "service_name": f"cnng-{self.profile_details['service']}",
                "caller": "configurator"
            })
            if s_action == "leave":
                self.c.functions.print_timer(40,"to gracefully leave the network")
                    
        self.c.functions.print_cmd_status({
            "text_start": "Updating Service",
            "brackets": f"{service} => {s_action}",
            "text_end": s_type,
            "status": "complete",
            "status_color": "green",
            "newline": True
        })   
        
    
    def is_duplicate_profile(self,profile_name):
        for profile in self.config_obj["profiles"].keys():
            if profile_name == profile:
                return True   
        return False
    
                         
    def move_config_backups(self):
        # move any backup configs out of the config dir and into the backup dir
        backup_dir = "empty"
        
        try:
            for key in self.c.config_obj["profiles"].keys():
                backup_dir = self.c.config_obj["profiles"][key]["dirs"]["backups"]
                break
        except: # global
            for key in self.config_obj["profiles"].keys():
                backup_dir = self.config_obj["profiles"][key]["backups"]
                break 
                       
        if backup_dir == "default":
            backup_dir = "/var/tessellation/backups/"  
                  
        if backup_dir == "empty":
            self.log.logger.warn("backup migration skipped.")
            if self.detailed:
                self.c.functions.print_paragraphs([
                    ["",1],["Configuration not moved to proper backup directory due to cancellation request.",1,"red"],
                    ["location retained:",0,"red"], [f"{self.config_path}",1,"yellow","bold"],
                    ["Configurations may contain sensitive information, please handle removal manually.",1,"magenta"]
                ])
                self.c.functions.print_any_key({})
        else:
            system(f"mv {self.config_path}cn-config_yaml_* {backup_dir} > /dev/null 2>&1")
            self.log.logger.info("configurator migrated all [cn-config.yaml] backups to first known backup directory")

        
    def ask_review_config(self):
        user_confirm = self.c.functions.confirm_action({
            "yes_no_default": "y",
            "return_on": "y",
            "prompt": "Review the created configuration?",
            "exit_if": False
        })   
        if user_confirm:           
            self.c.view_yaml_config("migrate")     
            
                               
if __name__ == "__main__":
    print("This class module is not designed to be run independently, please refer to the documentation")